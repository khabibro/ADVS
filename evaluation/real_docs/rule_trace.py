"""Print the submission-level rule results (rule type, outcome, documents and fields; NO values) for a folder of
documents, so a status can be traced to the rules that produced it.

    cd apps/api && PYTHONPATH=. .venv312/bin/python ../../evaluation/real_docs/rule_trace.py --files DIR [--workflow student]
"""
from __future__ import annotations

import argparse, json, os, runpy, sys, tempfile, unicodedata, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MIME = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}

ap = argparse.ArgumentParser()
ap.add_argument("--files", type=Path, required=True)
ap.add_argument("--workflow", default="student")
ap.add_argument("--eval-date", default=None)
a = ap.parse_args()
tmp = Path(tempfile.mkdtemp(prefix="advs_trace_"))
os.environ.update({"DATABASE_URL": f"sqlite:///{tmp / 't.db'}", "STORAGE_PATH": str(tmp / "s"), "OCR_PROVIDER": "paddle", "APP_ENV": "test", "LOG_LEVEL": "WARNING"})
sys.path.insert(0, str(REPO / "apps" / "api"))
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import Base, SessionLocal
from app.db.session import engine as eng
from app.main import app
from app.models.entities import Checklist, ValidationResult

assert str(tmp) in str(eng.url)
Base.metadata.create_all(eng)
runpy.run_path(str(REPO / "scripts" / "seed.py"))["main"]()
name = "학생 제출서류 점검" if a.workflow == "student" else "기업 제출서류 점검"
with SessionLocal() as db:
    cid = db.scalar(select(Checklist).where(Checklist.name == name)).id
manifest_date = a.eval_date
with TestClient(app, raise_server_exceptions=False) as c:
    pid = c.post("/api/v1/projects", json={"name": "trace", "workflow_id": str(cid)}).json()["id"]
    for f in sorted(a.files.iterdir()):
        if f.suffix.lower().lstrip(".") not in MIME:
            continue
        with f.open("rb") as fh:
            d = c.post(f"/api/v1/projects/{pid}/documents", files={"file": (unicodedata.normalize("NFC", f.name), fh, MIME[f.suffix.lower().lstrip('.')])}).json()
        c.post(f"/api/v1/documents/{d['id']}/process")
    v = c.post(f"/api/v1/projects/{pid}/verify", json={"evaluation_date": manifest_date or "2026-10-05"}).json()
    print("STATUS", v["status"], "| issues:", sorted({(i["code"], i.get("field_name")) for i in v["issues"]}))
    with SessionLocal() as db:
        rows = db.scalars(select(ValidationResult).where(ValidationResult.project_id == uuid.UUID(pid), ValidationResult.scope == "SUBMISSION")).all()
        for r in sorted(rows, key=lambda r: (r.rule_type, str(r.details))):
            det = r.details or {}
            print(f"  {r.rule_type:22s} {str(r.outcome):15s} {r.code:28s} {det.get('document_type') or ''} {det.get('field_name') or ''} {('<-> ' + str(det.get('related_document_type')) + '.' + str(det.get('related_field_name'))) if det.get('related_document_type') else ''}")
