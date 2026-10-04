"""A5 -- two read-only-on-production checks, run through the real FastAPI
service path against a scratch SQLite DB (never a shared/dev DB). No
production file is edited; the clock is monkeypatched only inside this
process for the B06 per-document comparison.

1. F-001 full-path check: business/B07_validity_missing/digital/ (4 files,
   one submission), run twice -- default checklist vs. a scratch checklist
   with one REQUIRED_FIELD rule for company_name on the social-insurance
   requirement specifically (the document type B07's bug concerns).
2. Validity-reference check: business/B06_expiry_on_submission_day/digital/,
   evaluated at 2026-10-05 and 2026-10-06, at both the submission level
   (evaluation_date is already an explicit API parameter -- no mock needed)
   and the per-document level (ValidationEngine uses date.today() internally
   -- mocked here only, to show whether it is day-dependent).

Source documents read from ~/Desktop/ADVS_test_variants/ (read-only, never
moved/modified -- Phase B does that).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VARIANTS = REPO_ROOT / "evaluation" / "datasets" / "synthetic" / "test_variants"

B07_DIR = VARIANTS / "business" / "B07_validity_missing" / "digital"
B06_DIR = VARIANTS / "business" / "B06_expiry_on_submission_day" / "digital"

results: dict = {}

with tempfile.TemporaryDirectory(prefix="advs_a5_") as temp_dir:
    temp_root = Path(temp_dir)
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_root / 'a5.db'}"
    os.environ["STORAGE_PATH"] = str(temp_root / "storage")
    os.environ["OCR_PROVIDER"] = "paddle"
    os.environ["APP_ENV"] = "test"
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ.setdefault(
        "PADDLE_OCR_CACHE_DIR", str(REPO_ROOT / "apps" / "api" / "storage" / "paddleocr-cache")
    )
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

    import runpy

    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.db.session import Base, SessionLocal, engine
    from app.main import app
    from app.models.entities import Checklist, DocumentRequirement, Project, User, ValidationRule
    from app.core.domain import DocumentType, RuleType, Severity

    Base.metadata.create_all(engine)
    seed = runpy.run_path(str(REPO_ROOT / "scripts" / "seed.py"))
    seed["main"]()

    with SessionLocal() as db:
        business = db.scalar(select(Checklist).where(Checklist.name == "기업 제출서류 점검"))
        user = db.scalar(select(User).where(User.email == "demo@advs.local"))
        business_id = business.id
        user_id = user.id

        # Scratch checklist: deep-copy the default business requirements,
        # then add exactly one REQUIRED_FIELD(company_name) rule to the
        # SOCIAL_INSURANCE_PAYMENT_CERTIFICATE requirement -- the document
        # type whose missing valid_until is what B07 tests, so the bug (if
        # present) suppresses the net for the field that is actually absent.
        scratch = Checklist(
            name="A5 scratch: single REQUIRED_FIELD(company_name)",
            description="A5 F-001 full-path probe, not used in production.",
            is_active=True,
        )
        db.add(scratch)
        db.flush()
        for req in business.requirements:
            new_req = DocumentRequirement(
                checklist_id=scratch.id, document_type=req.document_type, required=req.required
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
                        # NOTE: "company_name" is not a reviewable field for
                        # SOCIAL_INSURANCE_PAYMENT_CERTIFICATE (it has
                        # workplace_name instead) -- attempting that exact
                        # field name here is REJECTED by
                        # services/requirements.py::required_fields()'s
                        # "Unknown workflow-required canonical field" guard
                        # (confirmed by first running this script with
                        # "company_name" here and getting exactly that 400).
                        # Using this document type's own company-name-
                        # equivalent field instead, which the guard accepts,
                        # to test the actual bug mechanism on this document
                        # type's own required-field net.
                        params={"field": "workplace_name"},
                    )
                )
        db.commit()
        scratch_id = scratch.id

    def make_project(client, checklist_id, name):
        resp = client.post(
            "/api/v1/projects",
            json={"name": name, "workflow_id": str(checklist_id)},
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def upload_and_process(client, project_id, files_dir):
        doc_ids = []
        for path in sorted(files_dir.glob("*.pdf")):
            with path.open("rb") as fh:
                up = client.post(
                    f"/api/v1/projects/{project_id}/documents",
                    files={"file": (path.name, fh, "application/pdf")},
                )
            up.raise_for_status()
            doc_id = up.json()["id"]
            proc = client.post(f"/api/v1/documents/{doc_id}/process")
            proc.raise_for_status()
            doc_ids.append((path.name, doc_id, proc.json()))
        return doc_ids

    def verify(client, project_id, evaluation_date):
        resp = client.post(
            f"/api/v1/projects/{project_id}/verify",
            json={"evaluation_date": evaluation_date},
        )
        if resp.status_code >= 400:
            print("VERIFY ERROR BODY:", resp.text)
        resp.raise_for_status()
        return resp.json()

    with TestClient(app) as client:
        # ---------------- F-001 full-path check ----------------
        p1 = make_project(client, business_id, "A5-F001-default-checklist")
        docs1 = upload_and_process(client, p1, B07_DIR)
        v1 = verify(client, p1, "2026-10-05")

        p2 = make_project(client, scratch_id, "A5-F001-scratch-checklist")
        docs2 = upload_and_process(client, p2, B07_DIR)
        v2 = verify(client, p2, "2026-10-05")

        results["f001"] = {
            "literal_config_as_instructed": {
                "attempted": "REQUIRED_FIELD rule with params.field='company_name' on the "
                              "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE requirement",
                "result": "REJECTED at configuration time (400 VALIDATION_FAILED, "
                          "'Unknown workflow-required canonical field') -- "
                          "services/requirements.py::required_fields() checks the named field "
                          "against REVIEWABLE_FIELDS[document_type] and refuses an unknown one. "
                          "'company_name' is not a field this document type has (it has "
                          "'workplace_name' instead), so the exact scenario as literally stated "
                          "cannot be configured at all for this document type.",
                "substituted_with": "field='workplace_name' (this document type's own "
                                     "company-name-equivalent field) to test the actual bug "
                                     "mechanism below.",
            },
            "default_checklist": {
                "submission_status": v1.get("status"),
                "issues": [
                    {"code": i.get("code"), "document_type": i.get("document_type")}
                    for i in v1.get("issues", [])
                ],
                "documents": [
                    {"filename": fn, "processing_status": pr.get("processing_status"),
                     "document_type": pr.get("document_type")}
                    for fn, _did, pr in docs1
                ],
            },
            "scratch_checklist_required_field_workplace_name_on_social_insurance": {
                "submission_status": v2.get("status"),
                "issues": [
                    {"code": i.get("code"), "document_type": i.get("document_type")}
                    for i in v2.get("issues", [])
                ],
                "documents": [
                    {"filename": fn, "processing_status": pr.get("processing_status"),
                     "document_type": pr.get("document_type")}
                    for fn, _did, pr in docs2
                ],
            },
        }

        # ---------------- B06 validity-reference check ----------------
        p3 = make_project(client, business_id, "A5-B06-validity")
        docs3 = upload_and_process(client, p3, B06_DIR)
        v_oct5 = verify(client, p3, "2026-10-05")
        v_oct6 = verify(client, p3, "2026-10-06")

        # Per-document status (the GET /documents/{id} path), which uses
        # ValidationEngine's internal date.today() -- mocked here only, to
        # show whether *that* code path is day-dependent too. Find the
        # 납세증명서 (NATIONAL_TAX_PAYMENT_CERTIFICATE) document specifically,
        # since that's the one carrying valid_until in this set.
        tax_doc_id = next(
            did for fn, did, pr in docs3 if pr.get("document_type") == "NATIONAL_TAX_PAYMENT_CERTIFICATE"
        )

        import datetime as _dt
        from app.document_intelligence.validation import engine as _engine_mod

        class _FixedDate(_dt.date):
            _fixed = _dt.date(2026, 10, 5)

            @classmethod
            def today(cls):
                return cls._fixed

        real_date = _engine_mod.date
        _engine_mod.date = _FixedDate
        _FixedDate._fixed = _dt.date(2026, 10, 5)
        doc_detail_oct5 = client.get(f"/api/v1/documents/{tax_doc_id}").json()
        _FixedDate._fixed = _dt.date(2026, 10, 6)
        doc_detail_oct6 = client.get(f"/api/v1/documents/{tax_doc_id}").json()
        _engine_mod.date = real_date

        def issue_codes(detail):
            return sorted(
                {r.get("code") for r in detail.get("validation_results", []) if not r.get("passed")}
            )

        results["b06"] = {
            "submission_level": {
                "evaluation_date_2026-10-05": {
                    "status": v_oct5.get("status"),
                    "issues": [i.get("code") for i in v_oct5.get("issues", [])],
                },
                "evaluation_date_2026-10-06": {
                    "status": v_oct6.get("status"),
                    "issues": [i.get("code") for i in v_oct6.get("issues", [])],
                },
                "same_result": v_oct5.get("status") == v_oct6.get("status"),
                "date_source": "explicit evaluation_date in the POST /projects/{id}/verify "
                                "request body -- NOT server date.today(); "
                                "SubmissionVerificationEngine's DATE_COMPARISON/EVALUATION_DATE "
                                "rule reads context.evaluation_date only.",
            },
            "per_document_level_national_tax_cert": {
                "server_clock_fixed_2026-10-05": {
                    "overall_status": doc_detail_oct5.get("overall_status"),
                    "issues": issue_codes(doc_detail_oct5),
                },
                "server_clock_fixed_2026-10-06": {
                    "overall_status": doc_detail_oct6.get("overall_status"),
                    "issues": issue_codes(doc_detail_oct6),
                },
                "same_result": (
                    doc_detail_oct5.get("overall_status") == doc_detail_oct6.get("overall_status")
                    and issue_codes(doc_detail_oct5) == issue_codes(doc_detail_oct6)
                ),
                "date_source": "ValidationEngine._always_on_expiration_issues / "
                                "_handle_date_not_expired / _handle_issue_date_max_age call "
                                "date.today() directly (app/document_intelligence/validation/"
                                "engine.py lines ~168, ~279, ~311) -- the server's local clock, "
                                "with no injectable reference date and no explicit timezone. "
                                "Monkeypatched in THIS PROCESS ONLY for this comparison; the "
                                "file on disk was never edited.",
            },
        }

OUT = REPO_ROOT / "evaluation" / "phase_a_baseline" / "A5_checks.json"
OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))
