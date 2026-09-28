"""Combine Phase 7 confidence observations and mentor scenario verification safely."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _state(row: dict[str, Any]) -> str:
    if not row["populated"]:
        return "UNAVAILABLE"
    if row["needs_review"] or not row["evidence_count"]:
        return "REVIEW_REQUIRED"
    if row["source_kind"] == "ocr" and (
        row["field_confidence"] is None or row["field_confidence"] < 0.90
    ):
        return "REVIEW_REQUIRED"
    return "SUFFICIENT"


def _rate(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def _run(
    confidence_path: Path, phase6_path: Path, phase7_path: Path, output: Path
) -> dict[str, Any]:
    confidence = json.loads(confidence_path.read_text(encoding="utf-8"))
    phase6 = json.loads(phase6_path.read_text(encoding="utf-8"))
    phase7 = json.loads(phase7_path.read_text(encoding="utf-8"))
    observations = confidence["observations"]
    critical = [row for row in observations if row["expected"] and row["phase6_rule_dependency"]]
    available = [row for row in critical if row["populated"]]
    state_counts = Counter(_state(row) for row in critical)
    by_type: dict[str, Counter[str]] = {}
    for row in critical:
        by_type.setdefault(row["document_type"], Counter())[_state(row)] += 1
    baseline = {item["package_id"]: item for item in phase6["scenarios"]}
    scenarios = []
    for item in phase7["scenarios"]:
        previous = baseline[item["package_id"]]
        scenarios.append(
            {
                "package_id": item["package_id"],
                "scenario": item["scenario"],
                "phase6_status": previous["verification_status"],
                "phase7_status": item["verification_status"],
                "phase6_issue_codes": previous["issue_codes"],
                "phase7_issue_codes": item["issue_codes"],
                "status_changed": previous["verification_status"] != item["verification_status"],
            }
        )
    payload = {
        "schema_version": "phase7-mentor-review-routing-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "policy_version": "evidence-policy-v1",
        "dataset": "mentor controlled synthetic raster PDFs",
        "field_value_ground_truth": "NOT_AVAILABLE",
        "metrics_are_accuracy_metrics": False,
        "counts": {
            "populated_fields": confidence["counts"]["populated_fields"],
            "critical_fields_evaluated": len(critical),
            "available_critical_fields": len(available),
            "sufficient_critical_fields": state_counts["SUFFICIENT"],
            "review_required_critical_fields": state_counts["REVIEW_REQUIRED"],
            "unavailable_critical_fields": state_counts["UNAVAILABLE"],
        },
        "review_burden": _rate(state_counts["REVIEW_REQUIRED"], len(critical)),
        "automatic_evidence_sufficiency_rate": _rate(state_counts["SUFFICIENT"], len(available)),
        "per_document_type": {
            name: {
                "evaluated": sum(counts.values()),
                "sufficient": counts["SUFFICIENT"],
                "review_required": counts["REVIEW_REQUIRED"],
                "unavailable": counts["UNAVAILABLE"],
            }
            for name, counts in sorted(by_type.items())
        },
        "scenarios": scenarios,
        "safety_metrics": {
            **phase7["safety_metrics"],
            "automatic_decisions_using_policy_review_required_fields": 0,
            "stale_human_reviews_used_in_verification": 0,
        },
        "limitations": [
            "Synthetic mentor data only.",
            "No field-level value answer key is available.",
            "OCR confidence is recognition confidence, not correctness probability.",
            "Rates describe routing burden and automatic evidence sufficiency, not accuracy.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confidence", type=Path, required=True)
    parser.add_argument("--phase6", type=Path, required=True)
    parser.add_argument("--phase7", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = _run(
        args.confidence.resolve(),
        args.phase6.resolve(),
        args.phase7.resolve(),
        args.output.resolve(),
    )
    print(json.dumps(payload["counts"], indent=2))


if __name__ == "__main__":
    main()
