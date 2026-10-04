"""Confirm B-2 end-to-end: the same B06 document, read at two different
SERVER CLOCK dates, now gives the SAME per-document result -- unlike
Phase A's A5 check (pre-fix), which found this path flipped
REVIEW_REQUIRED -> NEEDS_CORRECTION/EXPIRED_DOCUMENT between 2026-10-05
and 2026-10-06. The submission's own date (created_at) doesn't move just
because the server clock does.
"""
import datetime as _dt
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VARIANTS_ROOT = REPO_ROOT / "evaluation" / "datasets" / "synthetic" / "test_variants"
B06_DIR = VARIANTS_ROOT / "business" / "B06_expiry_on_submission_day" / "digital"

with tempfile.TemporaryDirectory(prefix="advs_b2_confirm_") as temp_dir:
    temp_root = Path(temp_dir)
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_root / 'confirm.db'}"
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
    from app.models.entities import Checklist

    Base.metadata.create_all(engine)
    seed = runpy.run_path(str(REPO_ROOT / "scripts" / "seed.py"))
    seed["main"]()

    with SessionLocal() as db:
        business_id = db.scalar(select(Checklist).where(Checklist.name == "기업 제출서류 점검")).id

    with TestClient(app) as client:
        proj = client.post(
            "/api/v1/projects", json={"name": "b2-confirm", "workflow_id": str(business_id)}
        ).json()
        doc_ids = []
        for path in sorted(B06_DIR.glob("*.pdf")):
            with path.open("rb") as fh:
                up = client.post(
                    f"/api/v1/projects/{proj['id']}/documents",
                    files={"file": (path.name, fh, "application/pdf")},
                )
            doc_id = up.json()["id"]
            client.post(f"/api/v1/documents/{doc_id}/process")
            doc_ids.append((path.name, doc_id))

        import unicodedata

        tax_doc_id = next(
            did
            for fn, did in doc_ids
            if "납세증명서" in unicodedata.normalize("NFC", fn)
            and "사업자" not in unicodedata.normalize("NFC", fn)
        )

        import app.document_intelligence.validation.engine as engine_mod

        real_date = engine_mod.date

        class FixedServerClock(real_date):
            _fixed = real_date(2026, 10, 5)

            @classmethod
            def today(cls):
                return cls._fixed

        engine_mod.date = FixedServerClock

        FixedServerClock._fixed = real_date(2026, 10, 5)
        detail_oct5 = client.get(f"/api/v1/documents/{tax_doc_id}").json()
        FixedServerClock._fixed = real_date(2026, 10, 6)
        detail_oct6 = client.get(f"/api/v1/documents/{tax_doc_id}").json()
        FixedServerClock._fixed = real_date(2026, 12, 4)  # 60 days later
        detail_60d = client.get(f"/api/v1/documents/{tax_doc_id}").json()

        engine_mod.date = real_date

        def codes(d):
            return sorted({r["code"] for r in d.get("validation_results", []) if not r["passed"]})

        result = {
            "note": "server clock mocked in this process only; production file not edited",
            "oct5": {"overall_status": detail_oct5.get("overall_status"), "issue_codes": codes(detail_oct5)},
            "oct6": {"overall_status": detail_oct6.get("overall_status"), "issue_codes": codes(detail_oct6)},
            "60_days_later": {
                "overall_status": detail_60d.get("overall_status"),
                "issue_codes": codes(detail_60d),
            },
            "stable_across_server_clock": (
                detail_oct5.get("overall_status")
                == detail_oct6.get("overall_status")
                == detail_60d.get("overall_status")
                and codes(detail_oct5) == codes(detail_oct6) == codes(detail_60d)
            ),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        (REPO_ROOT / "evaluation" / "phase_b" / "B2_day_stability_confirmation.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
