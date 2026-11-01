"""Run a folder of real documents through the production API path (live PaddleOCR, scratch DB).

Contains no document content. Output goes to --out (keep it under data/private_real/, which is git-ignored).

    cd apps/api && PYTHONPATH=. .venv312/bin/python ../../evaluation/real_docs/run_real.py \
        --files ../../data/private_real/originals --eval-date 2026-08-03 --out ../../data/private_real/results/baseline
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import subprocess
import sys
import tempfile
import uuid
import time
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MIME = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
        "tif": "image/tiff", "tiff": "image/tiff", "bmp": "image/bmp"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", type=Path, default=None, help="folder (all supported files) or a single file")
    ap.add_argument("--eval-date", default="2026-08-03")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workflow", choices=["student", "business"], default="student")
    ap.add_argument("--strategy", default=None, help="auto-accept strategy override (default: the app's)")
    ap.add_argument("--label", default="run")
    ap.add_argument("--submissions", type=Path, default=None, help="SUBMISSIONS.json of a variant set (files are resolved next to it)")
    ap.add_argument("--repeat", type=int, default=1, help="run the file set N times in this process (determinism check)")
    ap.add_argument("--each", action="store_true", help="also run every file as its own submission")
    ap.add_argument("--memo-ocr", action="store_true", help="read each distinct file with OCR once per run (the output is deterministic); the same bytes in another submission reuse it")
    ap.add_argument("--ocr-cache", type=Path, default=None, help="persistent OCR cache (sha256 -> pages, plus second-pass regions): a miss reads with OCR and stores, a hit replays, so a later run on the same files needs no OCR")
    ap.add_argument("--applicant-from-gold", type=Path, default=None, help="WHAT-IF only: give every project the applicant name (student) / company name (business) of this gold file, as if the application form had been filled in. Never a default; the report must say so")
    ap.add_argument("--drop-requirement", default=None, help="also create a copy of the workflow without this document type; a submission selects it with \"workflow\": \"reduced\"")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="advs_real_"))
    os.environ.update({"DATABASE_URL": f"sqlite:///{tmp / 'real.db'}", "STORAGE_PATH": str(tmp / "storage"), "OCR_PROVIDER": "paddle",
                       "APP_ENV": "test", "LOG_LEVEL": "WARNING"})
    os.environ.setdefault("PADDLE_OCR_CACHE_DIR", str(REPO / "apps" / "api" / "storage" / "paddleocr-cache"))
    if args.strategy:
        os.environ["AUTO_ACCEPT_STRATEGY"] = args.strategy
    sys.path.insert(0, str(REPO / "apps" / "api"))
    sys.path.insert(0, str(REPO / "evaluation" / "harness"))
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.db.session import Base, SessionLocal
    from app.db.session import engine as db_engine
    from app.main import app
    from app.models.entities import Checklist, Document, OCRResult

    assert str(tmp) in str(db_engine.url), f"refusing to run against {db_engine.url}"
    Base.metadata.create_all(db_engine)
    runpy.run_path(str(REPO / "scripts" / "seed.py"))["main"]()
    name = "학생 제출서류 점검" if args.workflow == "student" else "기업 제출서류 점검"
    with SessionLocal() as db:
        checklist_id = db.scalar(select(Checklist).where(Checklist.name == name)).id
    reduced_id = None
    if args.drop_requirement:
        from app.models.entities import DocumentRequirement, ValidationRule

        with SessionLocal() as db:
            base = db.scalar(select(Checklist).where(Checklist.name == name))
            copy_ = Checklist(name=f"{name} (without {args.drop_requirement})", description=base.description, is_active=True)
            db.add(copy_)
            db.flush()
            for req in base.requirements:
                if req.document_type == args.drop_requirement:
                    continue
                new_req = DocumentRequirement(document_type=req.document_type, required=req.required)
                new_req.rules.extend(ValidationRule(rule_type=r.rule_type, severity=r.severity, params=dict(r.params)) for r in req.rules)
                copy_.requirements.append(new_req)
            db.commit()
            reduced_id = copy_.id
    if args.ocr_cache is not None:
        import app.services.processing as _processing
        from harness_core import OCRCacheProvider

        _real_factory = _processing.get_ocr_provider
        _cache = OCRCacheProvider(lambda settings: _real_factory(_processing.get_settings()), args.ocr_cache, "record")
        _processing.get_ocr_provider = lambda settings: _cache
    elif args.memo_ocr:
        import copy as _copy

        import app.services.processing as _processing

        _real_provider, _memo = _processing.get_ocr_provider, {}

        class _MemoProvider:
            def __init__(self, inner):
                self._inner = inner

            def __getattr__(self, attr):
                return getattr(self._inner, attr)

            async def extract_document(self, path, mime_type, filename):
                key = (hashlib.sha256(Path(path).read_bytes()).hexdigest(), mime_type)
                if key not in _memo:
                    _memo[key] = await self._inner.extract_document(path, mime_type, filename)
                return _copy.deepcopy(_memo[key])

        _processing.get_ocr_provider = lambda settings: _MemoProvider(_real_provider(settings))
    from harness_core import Runner

    application: dict[str, str] = {}
    if args.applicant_from_gold is not None:
        gold_docs = json.loads(args.applicant_from_gold.read_text(encoding="utf-8"))["documents"]
        wanted = "student_name" if args.workflow == "student" else "company_name"
        for document in gold_docs.values():
            entry = (document.get("fields") or document).get(wanted)
            value = entry.get("value") if isinstance(entry, dict) else entry
            if value:
                application = {"applicant_name" if args.workflow == "student" else "company_name": str(value)}
                break

    if args.submissions is None and args.files is None:
        raise SystemExit("--files or --submissions is required")
    files = [] if args.files is None else [args.files] if args.files.is_file() else sorted(p for p in args.files.iterdir() if p.suffix.lower().lstrip(".") in MIME)
    args.out.mkdir(parents=True, exist_ok=True)
    sub_list = json.loads(args.submissions.read_text(encoding="utf-8")) if args.submissions else []
    meta = {"label": args.label, "eval_date": args.eval_date, "workflow": args.workflow, "strategy": args.strategy or "app default",
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
            "files": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
            "submissions": args.submissions.name if args.submissions else None}

    def run(client, group: list[Path] | None, tag: str, eval_date: str | None = None, extra_dates: list[str] | None = None, workflow: str | None = None) -> dict:
        wid = reduced_id if workflow == "reduced" and reduced_id is not None else checklist_id
        project = client.post("/api/v1/projects", json={"name": f"{args.label}-{tag}", "workflow_id": str(wid), **application})
        project.raise_for_status()
        pid = project.json()["id"]
        records = []
        for path in files if group is None else group:
            t0 = time.perf_counter()
            with path.open("rb") as fh:
                up = client.post(f"/api/v1/projects/{pid}/documents", files={"file": (unicodedata.normalize("NFC", path.name), fh, MIME[path.suffix.lower().lstrip('.')])})
            rec = {"file": path.name, "upload_status": up.status_code}
            if up.status_code == 201:
                did = up.json()["id"]
                rec["document_id"] = did
                pr = client.post(f"/api/v1/documents/{did}/process")
                rec["process_status_code"] = pr.status_code
                if pr.status_code == 200:
                    body = pr.json()
                    rec.update(processing_status=body.get("processing_status"), processing_error_code=body.get("processing_error_code"),
                               predicted_document_type=body.get("document_type"))
                rec["process_seconds"] = round(time.perf_counter() - t0, 2)
            else:
                rec["upload_error"] = up.text[:300]
            records.append(rec)
        verify = client.post(f"/api/v1/projects/{pid}/verify", json={"evaluation_date": eval_date or args.eval_date})
        details = {}
        for rec in records:
            if "document_id" in rec:
                d = client.get(f"/api/v1/documents/{rec['document_id']}")
                details[rec["file"]] = d.json() if d.status_code == 200 else {"error": d.status_code}
                if d.status_code == 200:
                    Runner._capture_detail(rec, d.json())
        reviews = client.get(f"/api/v1/projects/{pid}/review-items")
        overview = client.get(f"/api/v1/projects/{pid}/overview")
        ocr = {}
        with SessionLocal() as db:
            for rec in records:
                if "document_id" not in rec:
                    continue
                rows = db.scalars(select(OCRResult).where(OCRResult.document_id == uuid.UUID(rec["document_id"])).order_by(OCRResult.page_number)).all()
                ocr[rec["file"]] = [{"page": r.page_number, "text": r.normalized_text, "lines": r.lines, "metadata": r.metadata_json} for r in rows]
        extra = {}
        for d in extra_dates or []:  # re-verify the same uploaded submission on another inspection date (no re-OCR)
            vr = client.post(f"/api/v1/projects/{pid}/verify", json={"evaluation_date": d})
            extra[d] = vr.json() if vr.status_code == 200 else {"error": vr.text}
        out = {"tag": tag, "extra_verifications": extra, "verification": verify.json() if verify.status_code == 200 else {"error": verify.text},
               "review_items": reviews.json() if reviews.status_code == 200 else [], "overview": overview.json() if overview.status_code == 200 else None,
               "documents": records, "document_details": details}
        (args.out / f"{tag}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (args.out / f"{tag}_ocr.json").write_text(json.dumps(ocr, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        return out

    started = time.time()
    with TestClient(app, raise_server_exceptions=False) as client:
        combined = {"verification": {}}
        for sub in sub_list:
            group = [args.submissions.parent / name for name in sub["files"]]
            result = run(client, group, f"sub_{sub['id']}", sub.get("eval_date"), sub.get("extra_eval_dates"), sub.get("workflow"))
            print(f"{sub['id']:28s} {result['verification'].get('status')}", flush=True)
        if files:
            for n in range(args.repeat):
                combined = run(client, None, "submission_all" if args.repeat == 1 else f"submission_rep{n + 1}")
        if args.each and files:
            for f in files:
                run(client, [f], f"single_{hashlib.sha256(f.name.encode()).hexdigest()[:8]}")
    meta["runtime_seconds"] = round(time.time() - started, 1)
    (args.out / "META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("status:", combined["verification"].get("status"), "| issues:", [i.get("code") for i in combined["verification"].get("issues", [])])
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
