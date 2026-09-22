"""Evaluate supported mentor business-package scenarios through Phase 6.

The utility processes the four in-scope business PDFs in each supported
package through the real upload/OCR/persistence path, then invokes the
authoritative submission verification API with the mentor reference date.
It stores no filenames, field values, OCR text, or synthetic identities.
"""

from __future__ import annotations

import argparse
import json
import os
import runpy
import tempfile
import time
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MENTOR_EVALUATION_DATE = "2026-09-19"
EXPECTED_SCENARIOS = {
    "P001": {"label": "normal", "status": "READY", "code": None},
    "P002": {
        "label": "business_number_mismatch",
        "status": "NEEDS_CORRECTION",
        "code": "INFORMATION_MISMATCH",
    },
    "P003": {
        "label": "sme_expired",
        "status": "NEEDS_CORRECTION",
        "code": "EXPIRED_DOCUMENT",
    },
    "P004": {
        "label": "national_tax_expired",
        "status": "NEEDS_CORRECTION",
        "code": "EXPIRED_DOCUMENT",
    },
    "P005": {
        "label": "social_insurance_expired",
        "status": "NEEDS_CORRECTION",
        "code": "EXPIRED_DOCUMENT",
    },
    "P007": {
        "label": "ocr_uncertainty",
        "status": "REVIEW_REQUIRED",
        "code": "REQUIRED_FIELD_UNRESOLVED",
    },
}
IN_SCOPE_MARKERS = (
    "사업자등록증",
    "중소기업확인서",
    "국세 납세증명서",
    "4대 사회보험료 완납증명서",
)
DETERMINISTIC_FAILURE_CODES = {
    "INFORMATION_MISMATCH",
    "EXPIRED_DOCUMENT",
    "RULE_CONDITION_NOT_MET",
}


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _mentor_root() -> Path:
    matches = [
        item
        for item in (Path.home() / "Desktop").iterdir()
        if item.is_dir() and _nfc(item.name) == "학생용_가상데이터"
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one mentor folder, found {len(matches)}")
    return matches[0]


def _packages(root: Path) -> dict[str, list[Path]]:
    package_root = next(
        item for item in root.iterdir() if item.is_dir() and _nfc(item.name) == "패키지별"
    )
    discovered: dict[str, list[Path]] = {}
    for directory in package_root.iterdir():
        key = _nfc(directory.name)[:4]
        if key not in EXPECTED_SCENARIOS:
            continue
        files = [
            path
            for path in directory.glob("*.pdf")
            if any(marker in _nfc(path.name) for marker in IN_SCOPE_MARKERS)
        ]
        if len(files) != 4:
            raise RuntimeError(f"Expected four in-scope PDFs for {key}, found {len(files)}")
        discovered[key] = sorted(files, key=lambda path: _nfc(path.name))
    if set(discovered) != set(EXPECTED_SCENARIOS):
        raise RuntimeError(f"Unexpected package inventory: {sorted(discovered)}")
    return discovered


def _run(output: Path) -> dict[str, Any]:
    packages = _packages(_mentor_root())
    repository_root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory(prefix="advs_phase6_eval_") as temp_dir:
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

        from app.db.session import Base, SessionLocal, engine
        from app.main import app
        from app.models.entities import Checklist, ExtractedField, ValidationResult
        from app.services.verification import SUBMISSION_SCOPE

        Base.metadata.create_all(engine)
        seed = runpy.run_path(str(repository_root / "scripts" / "seed.py"))
        seed["main"]()
        with SessionLocal() as db:
            workflow = db.scalar(select(Checklist).where(Checklist.name == "기업 제출서류 점검"))
            if workflow is None:
                raise RuntimeError("Seeded business workflow was not found")
            workflow_id = str(workflow.id)

        evaluated: list[dict[str, Any]] = []
        started = time.perf_counter()
        with TestClient(app) as client:
            for package_id, paths in sorted(packages.items()):
                project_response = client.post(
                    "/api/v1/projects",
                    json={"name": f"Phase 6 mentor {package_id}", "workflow_id": workflow_id},
                )
                project_response.raise_for_status()
                project_id = project_response.json()["id"]
                processing_statuses = []
                for path in paths:
                    with path.open("rb") as source:
                        upload = client.post(
                            f"/api/v1/projects/{project_id}/documents",
                            files={"file": (path.name, source, "application/pdf")},
                        )
                    upload.raise_for_status()
                    process = client.post(f"/api/v1/documents/{upload.json()['id']}/process")
                    process.raise_for_status()
                    processing_statuses.append(process.json()["processing_status"])
                verification = client.post(
                    f"/api/v1/projects/{project_id}/verify",
                    json={"evaluation_date": MENTOR_EVALUATION_DATE},
                )
                verification.raise_for_status()
                result = verification.json()
                codes = sorted({issue["code"] for issue in result["issues"]})
                expected = EXPECTED_SCENARIOS[package_id]

                with SessionLocal() as db:
                    rows = db.scalars(
                        select(ValidationResult).where(
                            ValidationResult.project_id == uuid.UUID(project_id),
                            ValidationResult.scope == SUBMISSION_SCOPE,
                        )
                    ).all()
                    field_ids = {
                        uuid.UUID(value)
                        for row in rows
                        for value in (
                            (row.details or {}).get("field_id"),
                            (row.details or {}).get("related_field_id"),
                        )
                        if value
                    }
                    populated_ids = {
                        str(item.id)
                        for item in db.scalars(
                            select(ExtractedField).where(ExtractedField.id.in_(field_ids))
                        ).all()
                        if item.normalized_value is not None
                    }
                    null_derived_failures = sum(
                        row.code in DETERMINISTIC_FAILURE_CODES
                        and any(
                            field_id and field_id not in populated_ids
                            for field_id in (
                                (row.details or {}).get("field_id"),
                                (row.details or {}).get("related_field_id"),
                            )
                        )
                        for row in rows
                    )

                evaluated.append(
                    {
                        "package_id": package_id,
                        "scenario": expected["label"],
                        "processed_documents": sum(
                            status == "COMPLETED" for status in processing_statuses
                        ),
                        "expected_documents": 4,
                        "verification_status": result["status"],
                        "issue_codes": codes,
                        "unresolved_rule_count": sum(
                            item["outcome"] == "UNRESOLVED" for item in result["rule_results"]
                        ),
                        "agrees_with_metadata": result["status"] == expected["status"]
                        and (expected["code"] is None or expected["code"] in codes),
                        "null_derived_deterministic_failures": null_derived_failures,
                    }
                )

        payload = {
            "schema_version": "phase6-mentor-verification-v1",
            "generated_at": datetime.now(UTC).isoformat(),
            "evaluation_date": MENTOR_EVALUATION_DATE,
            "dataset": "mentor controlled synthetic business packages",
            "scope": "Four Phase 6 business document types; local-tax documents excluded",
            "field_value_ground_truth": "NOT_AVAILABLE",
            "runtime_seconds": round(time.perf_counter() - started, 2),
            "scenarios": evaluated,
            "safety_metrics": {
                "false_ready_known_problem_scenarios": sum(
                    item["package_id"] != "P001" and item["verification_status"] == "READY"
                    for item in evaluated
                ),
                "null_derived_deterministic_failures": sum(
                    item["null_derived_deterministic_failures"] for item in evaluated
                ),
            },
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = _run(args.output.resolve())
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
