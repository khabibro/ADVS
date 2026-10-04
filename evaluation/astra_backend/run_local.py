"""Local-only HTTP evaluation; private inputs/outputs stay outside the repository.

Run with --code-root pointing to an immutable source snapshot for a baseline.
No filenames are used as classifier hints: uploads use anonymous sample IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import runpy
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    root = args.code_root.resolve()
    private = args.private_dir.resolve()
    sys.path.insert(0, str(root / "apps/api"))
    inventory = json.loads((private / "inventory.private.json").read_text())
    gold = json.loads((private / "gold-v1.2.private.json").read_text())
    db_path = private / f"{args.phase}.sqlite"
    if db_path.exists():
        raise RuntimeError("Refusing to overwrite a historical evaluation database")
    cache = Path("/Users/admin/Documents/ADVS/apps/api/storage/paddleocr-cache")
    os.environ.update(
        DATABASE_URL=f"sqlite:///{db_path}",
        STORAGE_PATH=str(private / f"storage-{args.phase}"),
        OCR_PROVIDER="paddle",
        APP_ENV="test",
        LOG_LEVEL="WARNING",
        PADDLE_OCR_CACHE_DIR=str(cache),
        PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK="True",
    )
    from app.core.config import get_settings
    from app.db.session import Base, SessionLocal, engine
    from app.main import app
    from app.models.entities import Checklist, OCRResult
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    Base.metadata.create_all(engine)
    runpy.run_path(str(root / "scripts/seed.py"))["main"]()
    with SessionLocal() as db:
        workflows = {
            "BUSINESS": str(
                db.scalar(
                    select(Checklist).where(Checklist.name == "기업 제출서류 점검")
                ).id
            ),
            "STUDENT": str(
                db.scalar(
                    select(Checklist).where(Checklist.name == "학생 제출서류 점검")
                ).id
            ),
        }
    source_files = sorted(p for p in (root / "apps/api/app").rglob("*.py"))
    digest = hashlib.sha256()
    for path in source_files:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    metadata = {
        "phase": args.phase,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "evaluation_date": gold["evaluation_date"],
        "backend_tree_sha256": digest.hexdigest(),
        "dataset_version": gold["dataset_version"],
        "gold_version": gold["gold_version"],
        "provider": "PaddleOCR",
        "device": "cpu",
        "local_only": True,
        "runtime_packages": {
            p: importlib.metadata.version(p)
            for p in ["paddleocr", "paddlepaddle", "paddlex", "pymupdf", "pillow"]
        },
        "model_weight_files": {},
        "configuration": {
            "pdf_render_dpi": get_settings().paddle_ocr_render_dpi,
            "lang": get_settings().paddle_ocr_lang,
            "recognition_model": get_settings().paddle_ocr_rec_model_name,
            "detection_model": get_settings().paddle_ocr_det_model_name,
            "doc_orientation": get_settings().paddle_ocr_doc_orientation,
        },
    }
    for path in cache.rglob("*"):
        if path.is_file():
            metadata["model_weight_files"][str(path.relative_to(cache))] = (
                hashlib.sha256(path.read_bytes()).hexdigest()
            )
    git = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    metadata["git_commit"] = (
        git.stdout.strip()
        or json.loads((private / "starting_git.json").read_text())[
            "rev-parse HEAD"
        ].strip()
    )
    metadata["starting_patch_sha256"] = hashlib.sha256(
        (private / "starting.patch").read_bytes()
    ).hexdigest()
    records = []
    output = private / f"{args.phase}.private.json"
    with TestClient(app) as client:
        for item in inventory:
            sid = item["sample_id"]
            truth = gold["samples"][sid]
            doc_type = truth["document_type"]
            workflow = (
                "STUDENT"
                if doc_type in {"TRANSCRIPT", "ENROLLMENT_CERTIFICATE"}
                else "BUSINESS"
            )
            project = client.post(
                "/api/v1/projects",
                json={"name": sid, "workflow_id": workflows[workflow]},
            ).json()
            start = time.perf_counter()
            with Path(item["path"]).open("rb") as handle:
                upload = client.post(
                    f"/api/v1/projects/{project['id']}/documents",
                    files={"file": (sid + item["extension"], handle, item["mime"])},
                )
            record = {
                "sample_id": sid,
                "upload_ms": (time.perf_counter() - start) * 1000,
                "upload_status": upload.status_code,
                "expected_document_type": doc_type,
                "fields": {},
            }
            if upload.status_code != 201:
                record["processing_status"] = "UPLOAD_REJECTED"
                record["upload_error"] = upload.json()
            else:
                doc_id = upload.json()["id"]
                start = time.perf_counter()
                response = client.post(f"/api/v1/documents/{doc_id}/process")
                record["process_ms"] = (time.perf_counter() - start) * 1000
                record["process_http_status"] = response.status_code
                payload = client.get(f"/api/v1/documents/{doc_id}").json()
                record.update(
                    processing_status=payload.get("processing_status"),
                    predicted_document_type=payload.get("document_type"),
                    overall_status=payload.get("overall_status"),
                    classification_meta=payload.get("classification_meta"),
                    payload=payload,
                    process_response=response.json(),
                )
                for field in payload.get("extracted_fields", []):
                    record["fields"][field["field_name"]] = {
                        **field,
                        "value": field.get("normalized_value"),
                        "evidence_count": len(field.get("evidence") or []),
                    }
                with SessionLocal() as db:
                    rows = db.scalars(
                        select(OCRResult)
                        .where(OCRResult.document_id == uuid.UUID(doc_id))
                        .order_by(OCRResult.page_number)
                    ).all()
                    record["ocr_pages"] = [
                        {
                            "page_number": row.page_number,
                            "provider": row.provider,
                            "confidence": row.confidence,
                            "text": row.normalized_text,
                            "lines": row.lines,
                            "metadata": row.metadata_json,
                        }
                        for row in rows
                    ]
                verify = client.post(
                    f"/api/v1/projects/{project['id']}/verify",
                    json={"evaluation_date": gold["evaluation_date"]},
                )
                record["verify_http_status"] = verify.status_code
                record["verification"] = verify.json()
                record["project_status"] = (
                    client.get(f"/api/v1/projects/{project['id']}").json().get("status")
                )
            records.append(record)
            output.write_text(
                json.dumps(
                    {"metadata": metadata, "samples": records},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            print(
                json.dumps(
                    {
                        "sample_id": sid,
                        "phase": args.phase,
                        "status": record["processing_status"],
                        "ms": record.get("process_ms"),
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
