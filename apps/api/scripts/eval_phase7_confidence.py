"""Measure privacy-safe field evidence confidence on the read-only mentor PDFs.

This report is descriptive only. The mentor set has no field-level answer key,
so its confidence values cannot establish correctness probabilities.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_phase5_mentor import _discover_samples, _git_value, _locate_mentor_root

IMPORTANT_FIELDS = {
    "company_name",
    "workplace_name",
    "business_registration_number",
    "valid_from",
    "valid_until",
    "student_name",
    "university_name",
    "department",
    "student_id",
    "issue_date",
    "gpa",
    "gpa_scale",
}

PHASE6_DEPENDENCIES = {
    ("BUSINESS_REGISTRATION_CERTIFICATE", "business_registration_number"),
    ("BUSINESS_REGISTRATION_CERTIFICATE", "company_name"),
    ("SME_CONFIRMATION_CERTIFICATE", "business_registration_number"),
    ("SME_CONFIRMATION_CERTIFICATE", "company_name"),
    ("SME_CONFIRMATION_CERTIFICATE", "valid_until"),
    ("NATIONAL_TAX_PAYMENT_CERTIFICATE", "business_registration_number"),
    ("NATIONAL_TAX_PAYMENT_CERTIFICATE", "company_name"),
    ("NATIONAL_TAX_PAYMENT_CERTIFICATE", "valid_until"),
    ("SOCIAL_INSURANCE_PAYMENT_CERTIFICATE", "business_registration_number"),
    ("SOCIAL_INSURANCE_PAYMENT_CERTIFICATE", "workplace_name"),
    ("SOCIAL_INSURANCE_PAYMENT_CERTIFICATE", "valid_until"),
    ("ENROLLMENT_CERTIFICATE", "issue_date"),
    ("TRANSCRIPT", "issue_date"),
    ("TRANSCRIPT", "gpa"),
}


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(row["field_confidence"]) for row in rows if row["field_confidence"] is not None]
    return {
        "observation_count": len(rows),
        "numeric_confidence_count": len(values),
        "count": len(values),
        "min": min(values) if values else None,
        "p10": _percentile(values, 0.10),
        "p25": _percentile(values, 0.25),
        "median": _percentile(values, 0.50),
        "p75": _percentile(values, 0.75),
        "p90": _percentile(values, 0.90),
        "max": max(values) if values else None,
    }


def _group_statistics(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return {name: _statistics(items) for name, items in sorted(grouped.items())}


def _run(output: Path) -> dict[str, Any]:
    mentor_root = _locate_mentor_root()
    samples, excluded = _discover_samples(mentor_root)
    with tempfile.TemporaryDirectory(prefix="advs_phase7_confidence_") as temp_dir:
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

        from app.core.domain import EXPECTED_FIELDS, DocumentType
        from app.db.session import Base, SessionLocal, engine
        from app.main import app
        from app.models.entities import Checklist, DocumentRequirement

        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            workflow = Checklist(name="Phase 7 Confidence Analysis", description="Isolated")
            db.add(workflow)
            db.flush()
            for document_type in sorted({sample["expected_document_type"] for sample in samples}):
                db.add(
                    DocumentRequirement(
                        checklist_id=workflow.id, document_type=document_type, required=True
                    )
                )
            db.commit()
            workflow_id = str(workflow.id)

        observations: list[dict[str, Any]] = []
        started = time.perf_counter()
        with TestClient(app) as client:
            project = client.post(
                "/api/v1/projects",
                json={"name": "Phase 7 Confidence Analysis", "workflow_id": workflow_id},
            )
            project.raise_for_status()
            project_id = project.json()["id"]
            for sample in samples:
                path: Path = sample["path"]
                with path.open("rb") as source:
                    upload = client.post(
                        f"/api/v1/projects/{project_id}/documents",
                        files={"file": (path.name, source, "application/pdf")},
                    )
                upload.raise_for_status()
                document_id = upload.json()["id"]
                processed = client.post(f"/api/v1/documents/{document_id}/process")
                processed.raise_for_status()
                detail_response = client.get(f"/api/v1/documents/{document_id}")
                detail_response.raise_for_status()
                detail = detail_response.json()
                document_type = sample["expected_document_type"]
                expected = set(EXPECTED_FIELDS[DocumentType(document_type)])
                by_name = {item["field_name"]: item for item in detail["extracted_fields"]}
                for field_name in sorted(expected | set(by_name)):
                    field = by_name.get(field_name)
                    evidence = (field or {}).get("evidence") or []
                    source_kinds = sorted({item["source_kind"] for item in evidence})
                    observations.append(
                        {
                            "sample_id": sample["sample_id"],
                            "scenario": sample["scenario"],
                            "document_type": document_type,
                            "field_name": field_name,
                            "source_kind": source_kinds[0]
                            if len(source_kinds) == 1
                            else "mixed"
                            if source_kinds
                            else None,
                            "extraction_method": (field or {}).get("extraction_method"),
                            "field_confidence": (field or {}).get("confidence"),
                            "evidence_confidences": [item["confidence"] for item in evidence],
                            "evidence_count": len(evidence),
                            "needs_review": (field or {}).get("needs_review", True),
                            "expected": field_name in expected,
                            "populated": (field or {}).get("normalized_value") is not None,
                            "missing": (field or {}).get("normalized_value") is None,
                            "phase6_rule_dependency": (document_type, field_name)
                            in PHASE6_DEPENDENCIES,
                        }
                    )

    populated = [row for row in observations if row["populated"]]
    important = [row for row in populated if row["field_name"] in IMPORTANT_FIELDS]
    payload = {
        "schema_version": "phase7-confidence-analysis-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_value("rev-parse", "--short", "HEAD"),
        "git_dirty": bool(_git_value("status", "--porcelain")),
        "dataset": {
            "description": "Mentor-provided controlled synthetic raster PDFs",
            "mentor_pdf_count": len(samples) + excluded,
            "in_scope_count": len(samples),
            "excluded_local_tax_count": excluded,
            "field_value_ground_truth": "NOT_AVAILABLE",
            "limitation": "Confidence distributions are descriptive and are not calibrated correctness probabilities.",
        },
        "runtime_seconds": round(time.perf_counter() - started, 2),
        "counts": {
            "field_observations": len(observations),
            "populated_fields": len(populated),
            "missing_expected_fields": sum(
                row["expected"] and row["missing"] for row in observations
            ),
            "ocr_derived_populated_fields": sum(row["source_kind"] == "ocr" for row in populated),
            "embedded_text_populated_fields": sum(
                row["source_kind"] == "embedded_pdf_text" for row in populated
            ),
        },
        "by_document_type": _group_statistics(populated, "document_type"),
        "important_fields": _group_statistics(important, "field_name"),
        "by_source_kind": _group_statistics(populated, "source_kind"),
        "observations": observations,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = _run(args.output.resolve())
    print(
        json.dumps(
            {
                key: payload[key]
                for key in ("counts", "by_document_type", "important_fields", "by_source_kind")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
