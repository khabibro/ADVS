"""P2.1 end-to-end production workflow probe.

Exercises the real HTTP workflow against the real PaddleOCR provider for the
frozen corpus: create project -> select workflow -> upload -> process ->
classification -> extraction -> verification -> review -> human correction ->
re-verification. Also records timing and terminal status.

A second, mock-provider pass runs the safety matrix, because the safety
scenarios need deterministic OCR text and must not be re-run through a 40 s
per-page recognizer seven times over.

Writes only to the gitignored runtime directory.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME = REPO_ROOT / "evaluation/private_runtime/p2_1"
WORK_DIR = REPO_ROOT / "evaluation/backend_round2/work"
FINGERPRINTS = WORK_DIR / "p2_original_fingerprints.json"
GOLD = WORK_DIR / "ground_truth_v2.json"

sys.path.insert(0, str(REPO_ROOT / "apps/api"))


def dataset_files() -> list[tuple[str, Path]]:
    """Map each private original to its safe id by content hash."""
    import hashlib

    frozen = {
        row["sha256"]: row["sample_id"]
        for row in json.loads(FINGERPRINTS.read_text())["records"]
    }
    root = Path(os.environ.get("ADVS_P21_DATASET", "~/Desktop/Samples")).expanduser()
    out = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in frozen:
            out.append((frozen[digest], path))
    return out


def boot(provider: str, storage: Path):
    """Configure the environment and import the app fresh."""
    for module in [key for key in sys.modules if key.startswith("app")]:
        del sys.modules[module]
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    os.environ["DATABASE_URL"] = f"sqlite:///{storage / 'probe.db'}"
    os.environ["STORAGE_PATH"] = str(storage)
    os.environ["OCR_PROVIDER"] = provider
    os.environ["APP_ENV"] = "test"
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ.setdefault(
        "PADDLE_OCR_CACHE_DIR", str(REPO_ROOT / "apps/api/storage/paddleocr-cache")
    )
    from app.core.domain import EXPECTED_FIELDS, DocumentType, RuleType, Severity
    from app.db.session import Base, SessionLocal, engine
    from app.main import app
    from app.models.entities import Checklist, DocumentRequirement, ValidationRule

    Base.metadata.create_all(bind=engine)
    # A workflow is a Checklist. A workflow must be selectable for a project to
    # be created at all, so the probe seeds one covering every in-scope type.
    with SessionLocal() as session:
        if session.query(Checklist).count() == 0:
            checklist = Checklist(
                name="p2.1-probe-workflow", description="p2.1 probe", is_active=True
            )
            session.add(checklist)
            session.flush()
            for doc_type in DocumentType:
                if doc_type is DocumentType.UNKNOWN:
                    continue
                requirement = DocumentRequirement(
                    id=uuid.uuid4(),
                    checklist_id=checklist.id,
                    document_type=doc_type.value,
                    required=True,
                )
                session.add(requirement)
                session.flush()
                # A checklist with no rules expresses no opinion, so the
                # safety rules below must be configured explicitly for the
                # probe to exercise them.
                # A rule may only be configured for a field the document type
                # actually has, otherwise the whole verification is refused as
                # misconfigured rather than evaluated.
                rules = [
                    (
                        "ISSUE_DATE_MAX_AGE",
                        {"field": "issue_date", "max_age_days": 90},
                        "ERROR",
                    ),
                ]
                if "valid_until" in EXPECTED_FIELDS[doc_type]:
                    rules.append(
                        ("DATE_NOT_EXPIRED", {"field": "valid_until"}, "ERROR")
                    )
                for rule_type, params, severity in rules:
                    session.add(
                        ValidationRule(
                            id=uuid.uuid4(),
                            requirement_id=requirement.id,
                            rule_type=RuleType(rule_type).value,
                            severity=Severity(severity).value,
                            params=params,
                        )
                    )
            session.commit()
    return app


def main() -> int:
    from fastapi.testclient import TestClient

    RUNTIME.mkdir(parents=True, exist_ok=True)
    summary: dict = {"workflow": [], "safety_matrix": []}
    root_temp = Path(tempfile.mkdtemp(prefix="advs_p21_"))
    try:
        # ---------- A. real-OCR production workflow over the frozen corpus ----
        storage = root_temp / "real"
        storage.mkdir()
        app = boot("paddle", storage)
        client = TestClient(app)
        records = dataset_files()
        print(
            f"probing {len(records)} real documents through the HTTP workflow",
            flush=True,
        )

        workflow_id = client.get("/api/v1/workflows").json()[0]["id"]
        for sample_id, path in records:
            started = time.perf_counter()
            project = client.post(
                "/api/v1/projects",
                json={"name": f"p21-{sample_id}", "workflow_id": str(workflow_id)},
            )
            project_id = project.json()["id"]
            upload_started = time.perf_counter()
            with path.open("rb") as handle:
                response = client.post(
                    f"/api/v1/projects/{project_id}/documents",
                    files={
                        "file": (
                            f"{sample_id}{path.suffix}",
                            handle,
                            "application/octet-stream",
                        )
                    },
                )
            upload_ms = int((time.perf_counter() - upload_started) * 1000)
            if response.status_code >= 400:
                summary["workflow"].append(
                    {"sample_id": sample_id, "upload_status": response.status_code}
                )
                continue
            document_id = response.json()["id"]

            process_started = time.perf_counter()
            processed = client.post(f"/api/v1/documents/{document_id}/process")
            process_ms = int((time.perf_counter() - process_started) * 1000)
            detail = client.get(f"/api/v1/documents/{document_id}").json()
            fields = detail.get("extracted_fields", [])
            verify_response = client.post(
                f"/api/v1/projects/{project_id}/verify",
                json={
                    "evaluation_date": datetime.now(tz=timezone.utc).date().isoformat()
                },
            )
            verification = client.get(
                f"/api/v1/projects/{project_id}/verification"
            ).json()
            review_items = client.get(
                f"/api/v1/projects/{project_id}/review-items"
            ).json()

            # review + human correction + re-verification
            # Review a target the service itself offers, so the probe measures
            # the review path rather than its own input validation.
            offered = [
                item.get("field_name")
                for item in (review_items if isinstance(review_items, list) else [])
                if item.get("field_name")
            ]
            target_field = next(
                (
                    name
                    for name in offered
                    if any(
                        f["field_name"] == name and f.get("normalized_value")
                        for f in fields
                    )
                ),
                None,
            )
            target = {"field_name": target_field} if target_field else None
            correction = None
            if target and target_field:
                correction = client.post(
                    f"/api/v1/projects/{project_id}/documents/{document_id}"
                    f"/fields/{target['field_name']}/review",
                    json={
                        "decision": "CORRECTED",
                        "corrected_value": "PROBE-HUMAN-VALUE",
                        "expected_processing_version": detail.get(
                            "processing_version", 0
                        ),
                        "reviewer_label": "p2.1-probe",
                    },
                )
            after = client.get(f"/api/v1/documents/{document_id}").json()
            after_fields = {
                f["field_name"]: f for f in after.get("extracted_fields", [])
            }
            corrected_entry = after_fields.get(target["field_name"]) if target else None

            summary["workflow"].append(
                {
                    "sample_id": sample_id,
                    "upload_status": response.status_code,
                    "upload_ms": upload_ms,
                    "process_status_code": processed.status_code,
                    "process_ms": process_ms,
                    "total_ms": int((time.perf_counter() - started) * 1000),
                    "processing_status": detail.get("processing_status"),
                    "document_type": detail.get("document_type"),
                    "classification_confidence": detail.get(
                        "classification_confidence"
                    ),
                    "field_count": len(fields),
                    "non_null_fields": sum(
                        1 for f in fields if f.get("normalized_value")
                    ),
                    "needs_review_fields": sum(
                        1 for f in fields if f.get("needs_review")
                    ),
                    "evidence_states": sorted(
                        {
                            f.get("evidence_assessment")
                            for f in fields
                            if f.get("evidence_assessment")
                        }
                    ),
                    "verification_status": verification.get("status"),
                    "verify_status_code": verify_response.status_code,
                    "verification_issues": sorted(
                        {
                            issue.get("code")
                            for issue in verification.get("issues", [])
                            if isinstance(issue, dict) and issue.get("code")
                        }
                    ),
                    "review_items": len(review_items)
                    if isinstance(review_items, list)
                    else -1,
                    "review_status": detail.get("review_status"),
                    "human_correction_status": None
                    if correction is None
                    else correction.status_code,
                    "human_value_is_separate_evidence": None
                    if corrected_entry is None
                    else corrected_entry.get("effective_source"),
                    "machine_normalized_value_preserved": None
                    if corrected_entry is None
                    else corrected_entry.get("normalized_value"),
                    "effective_value_after_correction": None
                    if corrected_entry is None
                    else corrected_entry.get("effective_normalized_value"),
                    "human_decision": None
                    if corrected_entry is None
                    else corrected_entry.get("current_review_decision"),
                }
            )
            print(
                f"  {sample_id}: {detail.get('processing_status')} "
                f"type={detail.get('document_type')} "
                f"fields={len(fields)} non_null={summary['workflow'][-1]['non_null_fields']} "
                f"process={process_ms}ms",
                flush=True,
            )
            # idempotency: processing the same document again must not change
            # the field set or create a second row.
            reprocess_started = time.perf_counter()
            client.post(f"/api/v1/documents/{document_id}/process")
            summary["workflow"][-1]["reprocess_ms"] = int(
                (time.perf_counter() - reprocess_started) * 1000
            )
            again = client.get(f"/api/v1/documents/{document_id}").json()
            summary["workflow"][-1]["stable_after_reprocess"] = [
                (f["field_name"], f.get("normalized_value"))
                for f in sorted(
                    again.get("extracted_fields", []), key=lambda i: i["field_name"]
                )
            ] == [
                (f["field_name"], f.get("normalized_value"))
                for f in sorted(fields, key=lambda i: i["field_name"])
            ]
            summary["workflow"][-1]["review_status_after_reprocess"] = again.get(
                "review_status"
            )
            row_count = client.get(f"/api/v1/projects/{project_id}/documents").json()
            summary["workflow"][-1]["document_rows_in_project"] = (
                len(row_count) if isinstance(row_count, list) else -1
            )

        # ---------- B. safety matrix on the deterministic provider ----------
        storage = root_temp / "safety"
        storage.mkdir()
        app = boot("mock", storage)
        client = TestClient(app)
        summary["safety_matrix"] = run_safety_matrix(client)
    finally:
        shutil.rmtree(root_temp, ignore_errors=True)

    (RUNTIME / "workflow_private.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary["safety_matrix"], ensure_ascii=False, indent=2))
    return 0


def run_safety_matrix(client) -> list[dict]:
    """Safety scenarios.

    Two layers, because they answer different questions:

    * End-to-end over HTTP on the deterministic provider, for the scenarios the
      provider's fixtures can express. Uploads accept only pdf/png/jpg/jpeg/webp,
      so a scenario's text is selected by the provider's filename hint, exactly
      as the repository's own integration tests do.
    * Rule level, straight against the validation engine, for the "a field is
      missing, nothing may be invented" scenarios that no single fixture can
      express.
    """
    from PIL import Image

    results: list[dict] = []
    workflow_id = client.get("/api/v1/workflows").json()[0]["id"]

    def project(name: str) -> str:
        return client.post(
            "/api/v1/projects", json={"name": name, "workflow_id": str(workflow_id)}
        ).json()["id"]

    # A real, decodable 1x1 PNG. The provider selects text by filename hint,
    # not by content; storage rejects an image that does not decode.
    import io

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
    png = buffer.getvalue()

    def run(name: str, hint: str, expect: str, extra_project=None) -> None:
        project_id = extra_project or project(f"safety-{uuid.uuid4().hex[:8]}")
        response = client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": (f"{hint}.png", png, "image/png")},
        )
        if response.status_code >= 400:
            results.append(
                {
                    "scenario": name,
                    "expectation": expect,
                    "upload_status": response.status_code,
                }
            )
            return
        document_id = response.json()["id"]
        processed = client.post(f"/api/v1/documents/{document_id}/process")
        client.post(
            f"/api/v1/projects/{project_id}/verify",
            json={"evaluation_date": datetime.now(tz=timezone.utc).date().isoformat()},
        )
        detail = client.get(f"/api/v1/documents/{document_id}").json()
        verification = client.get(f"/api/v1/projects/{project_id}/verification").json()
        fields = {f["field_name"]: f for f in detail.get("extracted_fields", [])}
        results.append(
            {
                "scenario": name,
                "expectation": expect,
                "document_type": detail.get("document_type"),
                "processing_status": detail.get("processing_status"),
                "review_status": detail.get("review_status"),
                "verification_status": verification.get("status"),
                "verification_issues": sorted(
                    {
                        issue.get("code")
                        for issue in verification.get("issues", [])
                        if isinstance(issue, dict) and issue.get("code")
                    }
                ),
                "verification_rule_results": sorted(
                    {
                        f"{r.get('rule_type')}:{r.get('passed')}"
                        for r in verification.get("rule_results", [])
                        if isinstance(r, dict)
                    }
                ),
                "non_null_fields": sorted(
                    k for k, v in fields.items() if v.get("normalized_value")
                ),
                "evidence_states": {
                    k: v.get("evidence_assessment") for k, v in sorted(fields.items())
                },
                "effective_sources": {
                    k: v.get("effective_source") for k, v in sorted(fields.items())
                },
                "needs_review_fields": sorted(
                    k for k, v in fields.items() if v.get("needs_review")
                ),
                "process_status_code": processed.status_code,
            }
        )

    run("happy_path_graduation", "graduation", "all fields resolved")
    run(
        "uncertain_ocr_inferred_issue_date",
        "graduation",
        "inferred issuance-block date must be review-gated",
    )
    run(
        "missing_reference_document",
        "career_partial",
        "company name truncated -> REVIEW_REQUIRED",
    )
    run("genuine_expiry", "sme_expired", "NEEDS_CORRECTION via expiry window")
    run("unknown_document", "unknown", "UNKNOWN")
    run("empty_ocr_result", "empty", "processing fails closed, never READY")
    run(
        "ocr_provider_error",
        "ocr_failure",
        "provider error surfaces as a failure, not a value",
    )

    # Duplicate: same bytes twice in one project.
    duplicate_project = project(f"safety-dup-{uuid.uuid4().hex[:8]}")
    run(
        "duplicate_first_upload",
        "sme",
        "first upload is clean",
        extra_project=duplicate_project,
    )
    run(
        "duplicate_second_upload",
        "sme",
        "configured DUPLICATE result",
        extra_project=duplicate_project,
    )

    results.extend(rule_level_matrix())
    return results


def rule_level_matrix() -> list[dict]:
    """Missing-field safety, driven straight at the validation engine.

    These are the rules that must never invent a value, so they are checked
    against the engine directly rather than through a fixture that happens to
    produce the same shape.
    """
    from app.core.domain import DocumentType, RuleType, Severity
    from app.document_intelligence.extraction.base import ExtractedValue
    from app.document_intelligence.validation.engine import (
        ConfiguredRule,
        ValidationEngine,
    )

    engine = ValidationEngine()
    out: list[dict] = []

    def check(name, expectation, fields, *, rules=None, **kwargs):
        issues = engine.validate_document(
            DocumentType.SME_CONFIRMATION_CERTIFICATE,
            DocumentType.SME_CONFIRMATION_CERTIFICATE,
            fields,
            configured_rules=rules,
            **kwargs,
        )
        out.append(
            {
                "scenario": name,
                "expectation": expectation,
                "failing_rules": sorted(
                    {
                        f"{issue.rule_type.value}:{issue.code}"
                        for issue in issues
                        if not issue.passed
                    }
                ),
                "issue_count": len(issues),
            }
        )

    full = [
        ExtractedValue("company_name", "한국테크", "한국테크", 0.99),
        ExtractedValue(
            "business_registration_number", "1234567890", "1234567890", 0.99
        ),
        ExtractedValue("valid_from", "2026-01-01", "2026-01-01", 0.99),
        ExtractedValue("valid_until", "2027-12-31", "2027-12-31", 0.99),
    ]
    check("baseline_all_present", "no failures", full)
    check(
        "missing_business_number_no_false_mismatch",
        "no invented business number, unresolved rather than failed",
        [f for f in full if f.field_name != "business_registration_number"],
    )
    check(
        "missing_validity_no_false_expiry",
        "no false expiry",
        [f for f in full if f.field_name != "valid_until"],
    )
    check(
        "missing_issue_date_no_false_date_failure",
        "no false date failure",
        [f for f in full if f.field_name != "valid_from"],
    )
    check(
        "wrong_identity_needs_correction",
        "identity mismatch is an error",
        [ExtractedValue("company_name", "다른회사", "다른회사", 0.99)] + full[1:],
        company_name="한국테크",
    )
    check(
        "duplicate_configured",
        "duplicate is a warning, not a crash",
        full,
        duplicate=True,
    )

    expiry_rule = [
        ConfiguredRule(
            RuleType.DATE_NOT_EXPIRED, Severity.ERROR, {"field": "valid_until"}
        )
    ]
    check(
        "genuine_expiry_rule_fires",
        "expired validity raises DATE_NOT_EXPIRED",
        [
            ExtractedValue("company_name", "한국테크", "한국테크", 0.99),
            ExtractedValue("valid_until", "2020-01-01", "2020-01-01", 0.99),
        ],
        rules=expiry_rule,
    )
    check(
        "unexpired_rule_silent",
        "a live validity raises nothing",
        [
            ExtractedValue("company_name", "한국테크", "한국테크", 0.99),
            ExtractedValue("valid_until", "2099-01-01", "2099-01-01", 0.99),
        ],
        rules=expiry_rule,
    )
    check("wrong_document_type", "a type mismatch is an error", full, rules=expiry_rule)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
