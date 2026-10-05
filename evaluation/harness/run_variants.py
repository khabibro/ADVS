"""Variant harness (raw capture; scoring lives in score_variants.py).

Runs the fictional test-variant document set
(evaluation/datasets/synthetic/test_variants/) through the real production
service path -- the same FastAPI routes the frontend calls: project create,
document upload, process, submission verify -- against a scratch SQLite
database created fresh for this run (never a shared/dev DB). No shortcut
around classification, extraction or the evidence-sufficiency policy.

The clock is fixed to the manifest's submission_date (2026-10-05) for the
duration of this process only, by monkeypatching `date.today()` in the one
module that still calls it directly
(app.document_intelligence.validation.engine). The submission-level
verification path already takes an explicit evaluation_date parameter and
needs no monkeypatch; it also receives that same date explicitly, so both
code paths agree. Nothing on disk is edited.

Usage (from apps/api):
    .venv312/bin/python ../../evaluation/harness/run_variants.py \\
        --output ../../evaluation/phase_c/B0_raw.json \\
        [--sets B01,B02,...] [--versions digital,scanned,images] [--skip-ocr]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import runpy
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
VARIANTS_ROOT = REPO_ROOT / "evaluation" / "datasets" / "synthetic" / "test_variants"
MANIFEST_PATH = VARIANTS_ROOT / "manifest.json"

EXT_MIME = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "bmp": "image/bmp",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _mime_for(path: Path) -> str:
    return EXT_MIME.get(path.suffix.lower().lstrip("."), "application/octet-stream")


def _comparable(value: Any) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sets", type=str, default=None, help="comma-separated set IDs, e.g. B01,B02")
    parser.add_argument(
        "--versions", type=str, default="digital,scanned,images",
        help="comma-separated: digital,scanned,images",
    )
    parser.add_argument("--skip-ocr", action="store_true", help="digital-only, skip scanned/images")
    parser.add_argument("--skip-formats", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    submission_date = manifest["submission_date"]

    versions = [v.strip() for v in args.versions.split(",") if v.strip()]
    if args.skip_ocr:
        versions = [v for v in versions if v == "digital"]
    wanted_sets = {s.strip() for s in args.sets.split(",")} if args.sets else None

    import tempfile

    temp_dir = tempfile.mkdtemp(prefix="advs_harness_", dir=str(REPO_ROOT / "evaluation" / "harness"))
    temp_root = Path(temp_dir)
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_root / 'harness.db'}"
    os.environ["STORAGE_PATH"] = str(temp_root / "storage")
    os.environ["OCR_PROVIDER"] = "paddle"
    os.environ["APP_ENV"] = "test"
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ.setdefault(
        "PADDLE_OCR_CACHE_DIR", str(REPO_ROOT / "apps" / "api" / "storage" / "paddleocr-cache")
    )
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.core.domain import DocumentType, RuleType, Severity
    from app.db.session import Base, SessionLocal, engine as db_engine
    from app.main import app
    from app.models.entities import Checklist, DocumentRequirement, User, ValidationRule
    from app.document_intelligence.validation import engine as validation_engine_module

    # Fix the clock for the per-document ValidationEngine's internal
    # date.today() calls (engine.py lines ~168, ~279, ~311) -- monkeypatched
    # in this process only, for the duration of this script. The submission
    # verify endpoint is called with an explicit evaluation_date below and
    # needs no patch.
    fixed = _dt.date.fromisoformat(submission_date)

    class _FixedDate(_dt.date):
        @classmethod
        def today(cls):
            return fixed

    validation_engine_module.date = _FixedDate

    Base.metadata.create_all(db_engine)
    seed = runpy.run_path(str(REPO_ROOT / "scripts" / "seed.py"))
    seed["main"]()

    with SessionLocal() as db:
        business_checklist = db.scalar(select(Checklist).where(Checklist.name == "기업 제출서류 점검"))
        student_checklist = db.scalar(select(Checklist).where(Checklist.name == "학생 제출서류 점검"))
        business_id = business_checklist.id
        student_id = student_checklist.id

        # B07's second condition: a scratch checklist identical to the
        # default business one, plus one REQUIRED_FIELD rule on the
        # social-insurance requirement. "company_name" is not a reviewable
        # field for that document type (it has workplace_name) and is
        # rejected by services/requirements.py's canonical-field guard if
        # used verbatim (confirmed in Phase A, A5) -- workplace_name is
        # used here, the field this bug actually governs for this document.
        b07_scratch = Checklist(
            name="B07 scratch: single REQUIRED_FIELD(workplace_name) on social insurance",
            description="Phase B harness probe for F-001, not used in production.",
            is_active=True,
        )
        db.add(b07_scratch)
        db.flush()
        for req in business_checklist.requirements:
            new_req = DocumentRequirement(
                checklist_id=b07_scratch.id, document_type=req.document_type, required=req.required
            )
            db.add(new_req)
            db.flush()
            for rule in req.rules:
                db.add(
                    ValidationRule(
                        requirement_id=new_req.id,
                        rule_type=rule.rule_type,
                        severity=rule.severity,
                        params=dict(rule.params),
                    )
                )
            if req.document_type == DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE.value:
                db.add(
                    ValidationRule(
                        requirement_id=new_req.id,
                        rule_type=RuleType.REQUIRED_FIELD.value,
                        severity=Severity.WARNING.value,
                        params={"field": "workplace_name"},
                    )
                )
        db.commit()
        b07_scratch_id = b07_scratch.id

    by_file = {entry["file"]: entry for entry in manifest["files"]}

    def make_project(client, checklist_id, name):
        resp = client.post("/api/v1/projects", json={"name": name, "workflow_id": str(checklist_id)})
        resp.raise_for_status()
        return resp.json()["id"]

    def upload_and_process(client, project_id, rel_paths):
        file_results = []
        for rel in rel_paths:
            path = VARIANTS_ROOT / rel
            t0 = time.perf_counter()
            mime = _mime_for(path)
            with path.open("rb") as fh:
                up = client.post(
                    f"/api/v1/projects/{project_id}/documents",
                    files={"file": (_nfc(path.name), fh, mime)},
                )
            record: dict[str, Any] = {"file": rel, "upload_status": up.status_code}
            if up.status_code != 201:
                try:
                    record["upload_error"] = up.json()
                except Exception:
                    record["upload_error"] = up.text
                file_results.append(record)
                continue
            doc_id = up.json()["id"]
            record["document_id"] = doc_id
            proc = client.post(f"/api/v1/documents/{doc_id}/process")
            record["process_status_code"] = proc.status_code
            if proc.status_code == 200:
                pj = proc.json()
                record["processing_status"] = pj.get("processing_status")
                record["processing_error_code"] = pj.get("processing_error_code")
                record["predicted_document_type"] = pj.get("document_type")
            detail = client.get(f"/api/v1/documents/{doc_id}")
            if detail.status_code == 200:
                dj = detail.json()
                record["classification_confidence"] = dj.get("classification_confidence")
                record["classification_needs_review"] = (dj.get("classification_meta") or {}).get(
                    "needs_review"
                )
                record["overall_status"] = dj.get("overall_status")
                record["fields"] = {
                    f["field_name"]: {
                        "value": f.get("effective_normalized_value"),
                        "machine_value": f.get("normalized_value"),
                        "confidence": f.get("confidence"),
                        "source": f.get("effective_source"),
                        "evidence_state": f.get("evidence_assessment"),
                        "needs_review": f.get("needs_review"),
                    }
                    for f in dj.get("extracted_fields", [])
                }
                record["page_count"] = dj.get("page_count")
                record["issues"] = [
                    r["code"] for r in dj.get("validation_results", []) if not r.get("passed")
                ]
            record["process_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            file_results.append(record)
        return file_results

    def verify(client, project_id, evaluation_date):
        resp = client.post(
            f"/api/v1/projects/{project_id}/verify", json={"evaluation_date": evaluation_date}
        )
        if resp.status_code != 200:
            return {"error": resp.text}
        v = resp.json()
        return {
            "status": v.get("status"),
            "issue_codes": [i.get("code") for i in v.get("issues", [])],
            "issues": v.get("issues", []),
        }

    results: dict[str, Any] = {
        "manifest_submission_date": submission_date,
        "versions_run": versions,
        "sets": {},
        "format_sets": {},
    }

    with TestClient(app, raise_server_exceptions=False) as client:
        all_scenario_sets = manifest["business_sets"] + manifest["student_sets"]
        for scenario in all_scenario_sets:
            set_id = scenario["set_id"]
            if wanted_sets is not None and set_id not in wanted_sets:
                continue
            workflow = scenario["workflow"]
            checklist_id = business_id if workflow == "business" else student_id
            results["sets"][set_id] = {"title": scenario["title"], "versions": {}}
            print(f"=== {set_id} — {scenario['title']} ===", flush=True)

            for version in versions:
                rel_paths = scenario["files"].get(version, [])
                if not rel_paths:
                    continue
                t0 = time.perf_counter()
                pid = make_project(client, checklist_id, f"{set_id}-{version}")
                file_results = upload_and_process(client, pid, rel_paths)
                sub = verify(client, pid, submission_date)
                elapsed = round(time.perf_counter() - t0, 1)
                expected_block = scenario["expected"].get(version, {})
                entry = {
                    "actual_submission_status": sub.get("status"),
                    "actual_issue_codes": sub.get("issue_codes"),
                    "files": file_results,
                    "elapsed_seconds": elapsed,
                }
                results["sets"][set_id]["versions"][version] = entry
                print(
                    f"  {version}: "
                    f"actual={sub.get('status')} ({elapsed}s)",
                    flush=True,
                )

            # B07's second condition: re-run the digital version only under
            # the scratch single-REQUIRED_FIELD checklist.
            if set_id == "B07" and "digital" in versions:
                rel_paths = scenario["files"]["digital"]
                t0 = time.perf_counter()
                pid = make_project(client, b07_scratch_id, "B07-digital-partial-checklist")
                file_results = upload_and_process(client, pid, rel_paths)
                sub = verify(client, pid, submission_date)
                elapsed = round(time.perf_counter() - t0, 1)
                results["sets"]["B07"]["versions"]["digital_partial_checklist"] = {
                    "checklist": "single REQUIRED_FIELD(workplace_name) on social-insurance "
                                 "requirement, otherwise identical to the default business checklist",
                    "actual_submission_status": sub.get("status"),
                    "actual_issue_codes": sub.get("issue_codes"),
                    "files": file_results,
                    "elapsed_seconds": elapsed,
                }
                print(
                    f"  digital_partial_checklist: actual={sub.get('status')} ({elapsed}s)",
                    flush=True,
                )

        if not args.skip_formats:
            for fset in manifest["format_sets"]:
                set_id = fset["set_id"]
                if wanted_sets is not None and set_id not in wanted_sets:
                    continue
                print(f"=== {set_id} (format) ===", flush=True)
                t0 = time.perf_counter()
                pid = make_project(client, business_id, f"{set_id}-format")
                file_results = upload_and_process(client, pid, fset["files"])
                elapsed = round(time.perf_counter() - t0, 1)
                results["format_sets"][set_id] = {
                    "title": fset["title"],
                    "expected": fset["expected"],
                    "files": file_results,
                    "elapsed_seconds": elapsed,
                }
                print(f"  {len(file_results)} files ({elapsed}s)", flush=True)

    validation_engine_module.date = _dt.date  # restore, though process exits anyway

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {args.output}")

    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
