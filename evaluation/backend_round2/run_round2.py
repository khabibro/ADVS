"""Real-document validation round 2: drive the production HTTP pipeline.

This harness deliberately goes through the *same* path the product uses:
FastAPI TestClient -> POST /projects/{id}/documents (upload + storage
validation) -> POST /documents/{id}/process (DocumentProcessingService:
PDF routing, OCR, classification, extraction, normalisation, evidence,
validation, persistence) -> GET /documents/{id} (read-back).

It never calls an extractor directly. That is the whole point: the question
under test is what a user uploading this file would actually get.

Privacy
-------
The harness reads ground truth from ``work/ground_truth.json`` (gitignored)
and writes its full record to ``work/round2_run.json`` (gitignored). The
committed summary is produced separately by ``summarise.py`` and contains no
document values, only per-field CORRECT / INCORRECT / UNRESOLVED verdicts
and opaque, non-reversible tokens.

Usage
-----
    cd apps/api
    ./.venv312/bin/python ../../evaluation/backend_round2/run_round2.py \
        --output ../../evaluation/backend_round2/work/round2_run.json

Everything runs on this machine. PaddleOCR runs on CPU; no network calls.
"""

from __future__ import annotations

import argparse
import json
import os
import runpy
import shutil
import tempfile
import time
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUND_DIR = REPO_ROOT / "evaluation" / "backend_round2"
WORK_DIR = ROUND_DIR / "work"

# Anonymous internal sample ids -> (Desktop filename, browser content-type).
# The id is what every artifact refers to; the filename never leaves this file
# except into work/ output, and the classifier receives it only because the
# upload endpoint stores it (see note in run() about filename evidence).
DATASET: list[tuple[str, str, str]] = [
    ("R2-01", "4대 사회보험료 완납증명서.pdf", "application/pdf"),
    ("R2-02", "사업자등록증.png", "image/png"),
    ("R2-03", "성적증명서.jpeg", "image/jpeg"),
    ("R2-04", "성적증명서.pdf", "application/pdf"),
    ("R2-05", "재학증명서.webp", "image/webp"),
    ("R2-06", "중소기업확인서.jpg", "image/jpeg"),
    ("R2-07", "재학증명서.pdf", "application/pdf"),
]


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def desktop_dirs() -> list[Path]:
    """Candidate directories that may hold the real sample files, in order.

    The owner's samples live in a `samples/` subfolder of ~/Desktop. The older
    resolution assumed they sat directly in ~/Desktop, which made every run
    fail with FileNotFoundError and silently blocked the whole evaluation.

    Resolution is read-only and never moves, renames or copies a source file:
    it only widens the set of directories searched. ADVS_SAMPLE_DIR overrides
    everything for a non-default location.
    """
    override = os.environ.get("ADVS_SAMPLE_DIR")
    if override:
        candidates = [Path(override).expanduser()]
    else:
        home = Path.home() / "Desktop"
        if not home.is_dir():
            raise RuntimeError(f"Desktop not found at {home}")
        # Names differ only by case on a case-insensitive filesystem, so a
        # plain containment probe is enough to find them all once.
        candidates = [home / name for name in ("samples", "Samples", "SAMPLES")]
        candidates.append(home)
    return [path for path in candidates if path.is_dir()]


def resolve_source(filename: str) -> Path:
    """Return the on-disk path for `filename`, trying both normalisations."""
    for base in desktop_dirs():
        for form in {unicodedata.normalize("NFC", filename), unicodedata.normalize("NFD", filename)}:
            candidate = base / form
            if candidate.is_file():
                return candidate
        # Last resort: scan with a normalisation-tolerant comparison, so an
        # unexpected third form (or a composed/composed difference we did not
        # anticipate) still resolves instead of silently vanishing.
        target = unicodedata.normalize("NFC", filename)
        for entry in base.iterdir():
            if entry.is_file() and unicodedata.normalize("NFC", entry.name) == target:
                return entry
    raise FileNotFoundError(f"Could not resolve {filename!r} in any Desktop sample directory")


def _comparable(value: Any) -> str:
    """Comparison form: strip all non-alphanumerics, lowercase.

    Mirrors what the product's own comparison does, so a verdict here means
    the same thing it would mean in verification.
    """
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _equal(expected: Any, actual: Any) -> bool:
    return _comparable(expected) == _comparable(actual)


def _verdict(expected: dict[str, Any], actual: str | None) -> str:
    """CORRECT / INCORRECT / UNRESOLVED / NOT_EVALUATED.

    The separation matters more than the score: a wrong non-null value is a
    safety problem, a missing one is merely a coverage problem, and collapsing
    them is how a system reports itself as accurate while emitting garbage.
    """
    category = expected["gt"]
    if category in {"AMBIGUOUS", "NOT_EVIDENCED"}:
        return "NOT_EVALUATED"
    if actual is None:
        return "UNRESOLVED"
    if category == "VERIFIED_ABSENT":
        return "INCORRECT" if str(actual).strip() else "CORRECT"
    if _equal(expected.get("value"), actual):
        return "CORRECT"
    return "INCORRECT"


def run(output: Path) -> dict[str, Any]:
    ground_truth = json.loads((WORK_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    samples = ground_truth["samples"]

    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="advs_round2_") as temp_dir:
        temp_root = Path(temp_dir)
        os.environ["DATABASE_URL"] = f"sqlite:///{temp_root / 'round2.db'}"
        os.environ["STORAGE_PATH"] = str(temp_root / "storage")
        os.environ["OCR_PROVIDER"] = "paddle"
        os.environ["APP_ENV"] = "test"
        os.environ["LOG_LEVEL"] = "WARNING"
        os.environ.setdefault(
            "PADDLE_OCR_CACHE_DIR",
            str(REPO_ROOT / "apps" / "api" / "storage" / "paddleocr-cache"),
        )

        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from app.db.session import Base, SessionLocal, engine
        from app.main import app
        from app.models.entities import (
            Checklist,
            Document,
            ExtractedField,
            OCRResult,
            Submission,
        )
        from app.document_intelligence.preprocessing.processor import (
            MIN_MEANINGFUL_TEXT_CHARS,
            is_meaningful_text,
        )

        Base.metadata.create_all(engine)
        seed = runpy.run_path(str(REPO_ROOT / "scripts" / "seed.py"))
        seed["main"]()
        with SessionLocal() as db:
            student_workflow = db.scalar(
                select(Checklist).where(Checklist.name == "학생 제출서류 점검")
            )
            business_workflow = db.scalar(
                select(Checklist).where(Checklist.name == "기업 제출서류 점검")
            )
            if student_workflow is None or business_workflow is None:
                raise RuntimeError("Seeded workflows were not found")
            workflow_ids = {
                "STUDENT": str(student_workflow.id),
                "BUSINESS": str(business_workflow.id),
            }

        records: list[dict[str, Any]] = []
        with TestClient(app) as client:
            for sample_id, filename, content_type in DATASET:
                truth = samples[sample_id]
                expected_type = truth["document_type"]
                workflow = "BUSINESS" if "PAYMENT" in expected_type or "BUSINESS" in expected_type or "SME" in expected_type else "STUDENT"

                record: dict[str, Any] = {
                    "sample_id": sample_id,
                    "filename": _nfc(filename),
                    "content_type": content_type,
                    "source_category": truth["source_category"],
                    "sensitivity": truth["sensitivity"],
                    "layout_family": truth["layout_family"],
                    "expected_document_type": expected_type,
                }
                source = resolve_source(filename)
                record["bytes"] = source.stat().st_size

                project = client.post(
                    "/api/v1/projects",
                    json={
                        "name": f"Round2 {sample_id}",
                        "workflow_id": workflow_ids[workflow],
                    },
                )
                project.raise_for_status()
                project_id = project.json()["id"]

                with source.open("rb") as handle:
                    upload = client.post(
                        f"/api/v1/projects/{project_id}/documents",
                        files={"file": (filename, handle, content_type)},
                    )
                record["upload_status"] = upload.status_code
                if upload.status_code != 201:
                    body = upload.json()
                    record["upload_rejected"] = {
                        "error_code": body.get("detail", {}).get("code"),
                        "http_status": upload.status_code,
                    }
                    record["processing_status"] = "NOT_UPLOADED"
                    records.append(record)
                    continue
                document_id = upload.json()["id"]
                record["document_id"] = document_id

                t0 = time.perf_counter()
                process = client.post(f"/api/v1/documents/{document_id}/process")
                record["process_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                record["process_status_code"] = process.status_code
                if process.status_code != 200:
                    body = process.json()
                    record["processing_status"] = "PROCESS_REQUEST_FAILED"
                    record["error_code"] = body.get("detail", {}).get("code")
                    records.append(record)
                    continue

                processed = process.json()
                record["processing_status"] = processed["processing_status"]
                record["processing_error_code"] = processed.get("error_code")
                record["predicted_document_type"] = processed.get("document_type")
                record["classification_confidence"] = processed.get(
                    "classification_confidence"
                )
                classification_meta = processed.get("classification_meta") or {}
                record["classification_needs_review"] = classification_meta.get(
                    "needs_review"
                )
                record["classification_evidence_count"] = len(
                    classification_meta.get("evidence") or []
                )
                record["classification_alternatives"] = [
                    item.get("document_type")
                    for item in classification_meta.get("alternatives") or []
                ]

                detail = client.get(f"/api/v1/documents/{document_id}")
                detail.raise_for_status()
                payload = detail.json()
                record["overall_status"] = payload.get("overall_status")
                record["missing_expected_fields"] = payload.get("missing_expected_fields")

                fields: dict[str, Any] = {}
                for field in payload.get("extracted_fields") or []:
                    name = field["field_name"]
                    value = field.get("normalized_value")
                    truth_entry = truth["fields"].get(name)
                    entry: dict[str, Any] = {
                        "populated": value is not None,
                        "needs_review": field.get("needs_review"),
                        "extraction_method": field.get("extraction_method"),
                        "confidence": field.get("confidence"),
                        "evidence_count": len(field.get("evidence") or []),
                        "evidence_pages": sorted(
                            {
                                item.get("page_number")
                                for item in field.get("evidence") or []
                                if item.get("page_number")
                            }
                        ),
                        "evidence_kinds": sorted(
                            {
                                item.get("source_kind")
                                for item in field.get("evidence") or []
                                if item.get("source_kind")
                            }
                        ),
                        "evidence_assessment": field.get("evidence_assessment"),
                        "effective_normalized_value": field.get(
                            "effective_normalized_value"
                        ),
                        "value": value,
                        "raw_value": field.get("raw_value"),
                        "source_text": field.get("source_text"),
                    }
                    if truth_entry is None:
                        entry["verdict"] = "NOT_EVALUATED"
                        entry["reason"] = "no ground truth for this field"
                    else:
                        entry["verdict"] = _verdict(truth_entry, value)
                        entry["gt_category"] = truth_entry["gt"]
                    fields[name] = entry

                # Fields the ground truth expects but the pipeline never emitted.
                for name, truth_entry in truth["fields"].items():
                    if name in fields:
                        continue
                    fields[name] = {
                        "populated": False,
                        "needs_review": None,
                        "extraction_method": None,
                        "confidence": None,
                        "evidence_count": 0,
                        "evidence_pages": [],
                        "value": None,
                        "raw_value": None,
                        "source_text": None,
                        "verdict": _verdict(truth_entry, None),
                        "gt_category": truth_entry["gt"],
                        "reason": "field row absent from persistence",
                    }
                record["fields"] = fields

                # Negative assertions: values the pipeline must never produce.
                negatives = []
                for assertion in truth.get("negative_assertions", []):
                    produced = fields.get(assertion["field"], {}).get("normalized_value")
                    negatives.append(
                        {
                            "field": assertion["field"],
                            "violated": produced is not None
                            and _comparable(produced) == _comparable(assertion["must_not_equal"]),
                            "reason": assertion["reason"],
                        }
                    )
                record["negative_assertions"] = negatives

                record["validation"] = [
                    {
                        "rule_type": item.get("rule_type"),
                        "code": item.get("code"),
                        "passed": item.get("passed"),
                        "severity": item.get("severity"),
                        "outcome": item.get("outcome"),
                    }
                    for item in payload.get("validation_results") or []
                ]

                with SessionLocal() as db:
                    doc_uuid = uuid.UUID(document_id)
                    ocr_rows = (
                        db.scalars(
                            select(OCRResult)
                            .where(OCRResult.document_id == doc_uuid)
                            .order_by(OCRResult.page_number)
                        )
                        .all()
                    )
                    record["pages"] = [
                        {
                            "page_number": row.page_number,
                            "provider": row.provider,
                            "char_count": len(row.normalized_text or ""),
                            "line_count": len(row.lines or []),
                            "mean_confidence": row.confidence,
                            "render_dpi": (row.metadata_json or {}).get("render_dpi"),
                            "source": (row.metadata_json or {}).get("source"),
                        }
                        for row in ocr_rows
                    ]
                    record["embedded_text_chars"] = sum(
                        len(row.normalized_text or "")
                        for row in ocr_rows
                        if row.provider == "direct_pdf_text"
                    )
                    record["ocr_chars"] = sum(
                        len(row.normalized_text or "")
                        for row in ocr_rows
                        if row.provider != "direct_pdf_text"
                    )
                    record["mean_ocr_confidence"] = _mean(
                        [
                            row.confidence
                            for row in ocr_rows
                            if row.provider != "direct_pdf_text" and row.confidence
                        ]
                    )
                    persisted = (
                        db.scalars(
                            select(ExtractedField).where(
                                ExtractedField.document_id == doc_uuid
                            )
                        )
                        .all()
                    )
                    record["persisted_field_count"] = len(persisted)
                    record["persisted_populated_count"] = sum(
                        1 for row in persisted if row.normalized_value is not None
                    )

                    # Read-back determinism: the detail endpoint must return
                    # what was persisted, not a re-derived answer.
                    reread = client.get(f"/api/v1/documents/{document_id}").json()
                    record["readback_stable"] = [
                        (f["field_name"], f.get("normalized_value"))
                        for f in reread.get("extracted_fields") or []
                    ] == [
                        (f["field_name"], f.get("normalized_value"))
                        for f in payload.get("extracted_fields") or []
                    ]

                    # Reprocessing must replace state, not append to it.
                    reprocess = client.post(f"/api/v1/documents/{document_id}/process")
                    record["reprocess_status_code"] = reprocess.status_code
                    if reprocess.status_code == 200:
                        after = db.scalars(
                            select(ExtractedField).where(
                                ExtractedField.document_id == doc_uuid
                            )
                        ).all()
                        record["reprocess_field_row_count"] = len(after)
                        record["reprocess_no_duplicate_rows"] = len(after) == len(
                            persisted
                        )
                        final = client.get(f"/api/v1/documents/{document_id}").json()
                        record["reprocess_type_stable"] = (
                            final.get("document_type")
                            == processed.get("document_type")
                        )
                        record["reprocess_fields_stable"] = [
                            (f["field_name"], f.get("normalized_value"))
                            for f in final.get("extracted_fields") or []
                        ] == [
                            (f["field_name"], f.get("normalized_value"))
                            for f in reread.get("extracted_fields") or []
                        ]

                record["pipeline"] = {
                    "used_production_http_path": True,
                    "extractors_called_directly": False,
                }
                records.append(record)

        payload = {
            "schema_version": "round2-real-pipeline-v1",
            "generated_at": datetime.now(UTC).isoformat(),
            "evaluation_date": ground_truth["evaluation_date"],
            "baseline_commit": os.environ.get("ROUND2_BASELINE_COMMIT", "unknown"),
            "runtime_seconds": round(time.perf_counter() - started, 1),
            "meaningful_text_threshold_chars": MIN_MEANINGFUL_TEXT_CHARS,
            "samples": records,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.output.resolve())
    shutil.rmtree(WORK_DIR / "inspect", ignore_errors=True)
    print(
        json.dumps(
            {
                "samples": len(payload["samples"]),
                "runtime_seconds": payload["runtime_seconds"],
                "processed": sum(
                    1
                    for item in payload["samples"]
                    if item.get("processing_status") == "COMPLETED"
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
