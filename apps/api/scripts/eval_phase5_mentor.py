"""Evaluate the read-only mentor PDF set through the production Phase 4 path.

This utility intentionally stores no OCR text, filenames, raw values, or
normalized values in its summary. The mentor README supplies document-type and
scenario ground truth, but it does not supply field-value ground truth, so the
summary reports completeness and normalization-shape validity rather than
claiming exact field accuracy.

Usage (from ``apps/api``):

    .venv312/bin/python scripts/eval_phase5_mentor.py \
        --output ../../evaluation/phase5/baseline_summary.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import unicodedata
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXPECTED_COUNTS = {
    "BUSINESS_REGISTRATION_CERTIFICATE": 7,
    "SME_CONFIRMATION_CERTIFICATE": 7,
    "NATIONAL_TAX_PAYMENT_CERTIFICATE": 7,
    "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE": 7,
    "ENROLLMENT_CERTIFICATE": 2,
    "TRANSCRIPT": 2,
}

TYPE_MARKERS = (
    ("4대 사회보험료 완납증명서", "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE", "social"),
    ("사업자등록증", "BUSINESS_REGISTRATION_CERTIFICATE", "business"),
    ("중소기업확인서", "SME_CONFIRMATION_CERTIFICATE", "sme"),
    ("국세 납세증명서", "NATIONAL_TAX_PAYMENT_CERTIFICATE", "national_tax"),
    ("재학증명서", "ENROLLMENT_CERTIFICATE", "enrollment"),
    ("성적증명서", "TRANSCRIPT", "transcript"),
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BUSINESS_NUMBER_RE = re.compile(r"^\d{10}$")
DECIMAL_RE = re.compile(r"^\d+(?:\.\d+)?$")


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    return result.stdout.strip()


def _locate_mentor_root() -> Path:
    desktop = Path.home() / "Desktop"
    candidates = [
        path
        for path in desktop.iterdir()
        if path.is_dir() and _nfc(path.name) == "학생용_가상데이터"
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one mentor folder, found {len(candidates)}")
    return candidates[0]


def _expected_type(path: Path) -> tuple[str, str] | None:
    name = _nfc(path.name)
    if "지방세 납세증명서" in name:
        return None
    for marker, document_type, slug in TYPE_MARKERS:
        if marker in name:
            return document_type, slug
    raise RuntimeError(f"Unsupported mentor PDF name: {name}")


def _scenario(path: Path) -> str:
    normalized = _nfc(str(path))
    package = re.search(r"P\d{3}", normalized)
    if package:
        return package.group(0)
    if "OCR불확실" in normalized:
        return "degraded"
    if "기준일초과" in normalized:
        return "reference_date_exceeded"
    return "normal"


def _discover_samples(root: Path) -> tuple[list[dict[str, Any]], int]:
    samples: list[dict[str, Any]] = []
    excluded = 0
    for path in sorted(root.rglob("*.pdf"), key=lambda item: _nfc(str(item))):
        expected = _expected_type(path)
        if expected is None:
            excluded += 1
            continue
        document_type, slug = expected
        scenario = _scenario(path)
        samples.append(
            {
                "sample_id": f"{scenario}_{slug}",
                "path": path,
                "expected_document_type": document_type,
                "scenario": scenario,
            }
        )
    counts = Counter(sample["expected_document_type"] for sample in samples)
    if dict(counts) != EXPECTED_COUNTS:
        raise RuntimeError(f"Unexpected mentor inventory: {dict(counts)}")
    if excluded != 6:
        raise RuntimeError(f"Expected six excluded local-tax PDFs, found {excluded}")
    return samples, excluded


def _normalization_shape(field_name: str, value: str | None) -> bool | None:
    if value is None:
        return None
    if field_name == "business_registration_number":
        return BUSINESS_NUMBER_RE.fullmatch(value) is not None
    if field_name.endswith("_date") or field_name in {"valid_from", "valid_until"}:
        return DATE_RE.fullmatch(value) is not None
    if field_name in {"gpa", "gpa_scale"}:
        return DECIMAL_RE.fullmatch(value) is not None
    return True


def _fingerprint(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _aggregate(samples: list[dict[str, Any]]) -> dict[str, Any]:
    processing_success = sum(sample["processing_status"] == "COMPLETED" for sample in samples)
    classification_correct = sum(sample["classification_correct"] for sample in samples)
    unknown_count = sum(sample["predicted_document_type"] == "UNKNOWN" for sample in samples)
    wrong_type_count = len(samples) - classification_correct - unknown_count
    expected_total = sum(sample["expected_field_count"] for sample in samples)
    populated_total = sum(sample["populated_expected_field_count"] for sample in samples)
    provenance_denominator = sum(sample["populated_field_count"] for sample in samples)
    provenance_numerator = sum(sample["evidenced_populated_field_count"] for sample in samples)
    normalization_checked = sum(sample["normalization_checked"] for sample in samples)
    normalization_valid = sum(sample["normalization_valid"] for sample in samples)

    return {
        "processing_success": {
            "numerator": processing_success,
            "denominator": len(samples),
            "rate": processing_success / len(samples),
        },
        "classification_accuracy": {
            "numerator": classification_correct,
            "denominator": len(samples),
            "rate": classification_correct / len(samples),
        },
        "unknown_count": unknown_count,
        "wrong_type_count": wrong_type_count,
        "expected_field_completeness": {
            "numerator": populated_total,
            "denominator": expected_total,
            "rate": populated_total / expected_total,
        },
        "exact_field_correctness": {
            "status": "NOT_EVALUATED",
            "reason": "Mentor materials provide no field-value ground truth.",
        },
        "normalization_shape_validity": {
            "numerator": normalization_valid,
            "denominator": normalization_checked,
            "rate": normalization_valid / normalization_checked if normalization_checked else None,
            "scope": "Populated fields with canonical shape constraints; not value correctness.",
        },
        "provenance_coverage": {
            "numerator": provenance_numerator,
            "denominator": provenance_denominator,
            "rate": provenance_numerator / provenance_denominator
            if provenance_denominator
            else None,
        },
        "missing_expected_field_count": expected_total - populated_total,
        "incorrect_populated_value_count": {
            "status": "NOT_EVALUATED",
            "reason": "Mentor materials provide no field-value ground truth.",
        },
    }


def _group_metrics(samples: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        grouped[sample[key]].append(sample)
    return {name: _aggregate(rows) for name, rows in sorted(grouped.items())}


def _field_metrics(samples: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, dict[str, int]] = defaultdict(
        lambda: {"expected": 0, "populated": 0, "evidenced": 0, "normalization_valid": 0}
    )
    for sample in samples:
        for field in sample["fields"]:
            if not field["expected"]:
                continue
            result = metrics[field["field_name"]]
            result["expected"] += 1
            if field["populated"]:
                result["populated"] += 1
                result["evidenced"] += int(field["evidence_count"] > 0)
                result["normalization_valid"] += int(
                    field["normalization_shape_valid"] is not False
                )
    return dict(sorted(metrics.items()))


def _run(output: Path) -> dict[str, Any]:
    mentor_root = _locate_mentor_root()
    discovered, excluded = _discover_samples(mentor_root)

    with tempfile.TemporaryDirectory(prefix="advs_phase5_eval_") as temp_dir:
        temp_root = Path(temp_dir)
        os.environ["DATABASE_URL"] = f"sqlite:///{temp_root / 'evaluation.db'}"
        os.environ["STORAGE_PATH"] = str(temp_root / "storage")
        os.environ["OCR_PROVIDER"] = "paddle"
        os.environ.setdefault(
            "PADDLE_OCR_CACHE_DIR",
            str(Path(__file__).resolve().parents[1] / "storage" / "paddleocr-cache"),
        )
        os.environ["APP_ENV"] = "test"
        os.environ["LOG_LEVEL"] = "WARNING"

        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from app.core.domain import EXPECTED_FIELDS, DocumentType
        from app.db.session import Base, SessionLocal, engine
        from app.document_intelligence.classification.classifier import CLASSIFIER_VERSION
        from app.document_intelligence.extraction.base import EXTRACTOR_VERSION
        from app.main import app
        from app.models.entities import Checklist, DocumentRequirement, OCRResult

        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            workflow = Checklist(name="Phase 5 Mentor Evaluation", description="Isolated")
            db.add(workflow)
            db.flush()
            for document_type in EXPECTED_COUNTS:
                db.add(
                    DocumentRequirement(
                        checklist_id=workflow.id,
                        document_type=document_type,
                        required=True,
                    )
                )
            db.commit()
            workflow_id = str(workflow.id)

        evaluated: list[dict[str, Any]] = []
        started = time.perf_counter()
        with TestClient(app) as client:
            project = client.post(
                "/api/v1/projects",
                json={"name": "Phase 5 Mentor Evaluation", "workflow_id": workflow_id},
            )
            project.raise_for_status()
            project_id = project.json()["id"]

            for sample in discovered:
                sample_started = time.perf_counter()
                path: Path = sample["path"]
                with path.open("rb") as source:
                    upload = client.post(
                        f"/api/v1/projects/{project_id}/documents",
                        files={"file": (path.name, source, "application/pdf")},
                    )
                upload.raise_for_status()
                document_id = upload.json()["id"]
                process = client.post(f"/api/v1/documents/{document_id}/process")
                process.raise_for_status()
                detail_response = client.get(f"/api/v1/documents/{document_id}")
                detail_response.raise_for_status()
                detail = detail_response.json()

                with SessionLocal() as db:
                    pages = db.scalars(
                        select(OCRResult).where(OCRResult.document_id == uuid.UUID(document_id))
                    ).all()

                expected_fields = EXPECTED_FIELDS[DocumentType(sample["expected_document_type"])]
                fields_by_name = {
                    field["field_name"]: field for field in detail["extracted_fields"]
                }
                field_results = []
                for field_name in sorted(set(expected_fields) | set(fields_by_name)):
                    field = fields_by_name.get(field_name)
                    normalized_value = field["normalized_value"] if field else None
                    evidence = field.get("evidence") or [] if field else []
                    field_results.append(
                        {
                            "field_name": field_name,
                            "expected": field_name in expected_fields,
                            "populated": normalized_value is not None,
                            "normalized_value_fingerprint": _fingerprint(normalized_value),
                            "normalization_shape_valid": _normalization_shape(
                                field_name, normalized_value
                            ),
                            "evidence_count": len(evidence),
                            "evidence_pages": sorted({item["page_number"] for item in evidence}),
                            "bbox_complete": all(
                                item.get("bounding_box") is not None for item in evidence
                            )
                            if evidence
                            else None,
                            "confidence_complete": all(
                                item.get("confidence") is not None for item in evidence
                            )
                            if evidence
                            else None,
                        }
                    )

                populated = [field for field in field_results if field["populated"]]
                expected_populated = [field for field in populated if field["expected"]]
                normalization_results = [
                    field["normalization_shape_valid"]
                    for field in populated
                    if field["normalization_shape_valid"] is not None
                ]
                evaluated.append(
                    {
                        "sample_id": sample["sample_id"],
                        "scenario": sample["scenario"],
                        "expected_document_type": sample["expected_document_type"],
                        "predicted_document_type": detail["document_type"],
                        "classification_correct": detail["document_type"]
                        == sample["expected_document_type"],
                        "classification_confidence": detail["classification_confidence"],
                        "processing_status": detail["processing_status"],
                        "error_code": detail["error_code"],
                        "expected_field_count": len(expected_fields),
                        "populated_expected_field_count": len(expected_populated),
                        "populated_field_count": len(populated),
                        "evidenced_populated_field_count": sum(
                            bool(field["evidence_count"]) for field in populated
                        ),
                        "missing_expected_fields": detail["missing_expected_fields"],
                        "normalization_checked": len(normalization_results),
                        "normalization_valid": sum(
                            result is not False for result in normalization_results
                        ),
                        "page_count": len(pages),
                        "ocr_provider": sorted({page.provider for page in pages}),
                        "ocr_line_count": sum(len(page.lines) for page in pages),
                        "page_average_confidence": [page.confidence for page in pages],
                        "fields": field_results,
                        "processing_ms": round((time.perf_counter() - sample_started) * 1000, 2),
                    }
                )

        elapsed = time.perf_counter() - started
        payload = {
            "schema_version": "phase5-mentor-eval-v1",
            "reproducibility": {
                "generated_at": datetime.now(UTC).isoformat(),
                "git_commit": _git_value("rev-parse", "--short", "HEAD"),
                "git_dirty": bool(_git_value("status", "--porcelain")),
                "ocr_provider": "paddle",
                "ocr_models": {
                    "detector": os.environ.get("PADDLE_OCR_DET_MODEL_NAME", "PP-OCRv5_mobile_det"),
                    "recognizer": os.environ.get(
                        "PADDLE_OCR_REC_MODEL_NAME", "korean_PP-OCRv5_mobile_rec"
                    ),
                },
                "classifier_version": CLASSIFIER_VERSION,
                "extractor_version": EXTRACTOR_VERSION,
                "evaluation_path": "HTTP upload -> storage -> DocumentProcessingService -> persisted GET",
                "runtime_seconds": round(elapsed, 2),
            },
            "dataset": {
                "description": "Mentor-provided controlled synthetic raster PDFs",
                "mentor_pdf_count": len(discovered) + excluded,
                "in_scope_count": len(discovered),
                "excluded_local_tax_count": excluded,
                "per_type": dict(
                    sorted(
                        Counter(sample["expected_document_type"] for sample in discovered).items()
                    )
                ),
                "field_value_ground_truth": "NOT_AVAILABLE",
            },
            "metrics": _aggregate(evaluated),
            "per_document_type": _group_metrics(evaluated, "expected_document_type"),
            "per_field": _field_metrics(evaluated),
            "samples": evaluated,
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = _run(args.output.resolve())
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
