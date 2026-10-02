"""Immutable, fixed-denominator field scoring, independent of extraction logic.

Precision is supported correct populated fields / *all* populated fields.
Unlabelled and ambiguous outputs cannot earn credit but remain visible in that
denominator. Recall only uses PRESENT assertions. Absence earns abstention, not
recall credit. No production normalizer is reused by the oracle.
"""

from __future__ import annotations

import copy
import statistics
import unicodedata
from collections import Counter
from typing import Any

SCORER_VERSION = "astra-safety-1.1"
STATE_ALIASES = {"VERIFIED": "PRESENT", "VERIFIED_ABSENT": "ABSENT", "PARTIAL": "AMBIGUOUS"}
VERDICTS = (
    "CORRECT",
    "INCORRECT",
    "UNRESOLVED",
    "CORRECTLY_ABSTAINED",
    "NOT_EVALUATED",
    "AMBIGUOUS_GROUND_TRUTH",
)


def populated(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def equal_value(expected: Any, actual: Any, field_name: str | None = None) -> bool:
    """Only Unicode/whitespace presentation differences are ignored."""

    def key(value: Any) -> str:
        text = "".join(unicodedata.normalize("NFC", str(value)).split())
        if field_name == "business_registration_number" and all(
            char.isdigit() or char in "-‐‑‒–—−" for char in text
        ):
            return "".join(char for char in text if char.isdigit())
        return text

    return key(expected) == key(actual)


def field_verdict(
    expected: dict[str, Any] | None, actual: Any, field_name: str | None = None
) -> str:
    if expected is None:
        return "NOT_EVALUATED"
    state = expected.get("state", expected.get("gt"))
    state = STATE_ALIASES.get(state, state)
    if state == "AMBIGUOUS":
        return "AMBIGUOUS_GROUND_TRUTH"
    if state in {"ABSENT", "NOT_EVIDENCED"}:
        return "INCORRECT" if populated(actual) else "CORRECTLY_ABSTAINED"
    if state != "PRESENT":
        raise ValueError(f"Unknown expected state: {state}")
    if not populated(actual):
        return "UNRESOLVED"
    return "CORRECT" if equal_value(expected["value"], actual, field_name) else "INCORRECT"


def score_run(run: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitized score without mutating run, gold, or old verdicts."""
    actuals = {r["sample_id"]: r for r in run["samples"]}
    if len(actuals) != len(run["samples"]):
        raise ValueError("Duplicate sample IDs in run")
    if set(actuals) - set(gold["samples"]):
        raise ValueError("Run contains samples outside fixed gold dataset")
    totals: Counter[str] = Counter()
    per_field: dict[str, Counter[str]] = {}
    confusion: dict[str, Counter[str]] = {}
    documents = []
    durations = []
    for sid, truth in gold["samples"].items():
        record = actuals.get(sid, {})
        fields = record.get("fields", {})
        predictions = record.get("predicted_document_type", "NOT_PROCESSED")
        expected_type = truth["document_type"]
        confusion.setdefault(expected_type, Counter())[predictions] += 1
        totals["classification_correct"] += predictions == expected_type
        totals["classification_abstained"] += predictions == "UNKNOWN"
        totals["processing_failures"] += record.get("processing_status") != "COMPLETED"
        rows = []
        for name in sorted(set(truth["fields"]) | set(fields)):
            assertion = truth["fields"].get(name)
            entry = fields.get(name, {})
            actual = entry.get("value")
            is_populated = populated(actual)
            verdict = field_verdict(assertion, actual, name)
            state = (assertion or {}).get("state", (assertion or {}).get("gt"))
            state = STATE_ALIASES.get(state, state)
            required = bool((assertion or {}).get("required", False))
            totals[verdict] += 1
            totals["populated"] += is_populated
            totals["present_assertions"] += state == "PRESENT"
            totals["populated_unlabelled"] += is_populated and assertion is None
            totals["populated_ambiguous"] += is_populated and state == "AMBIGUOUS"
            totals["unresolved_required"] += required and verdict in {
                "UNRESOLVED",
                "AMBIGUOUS_GROUND_TRUTH",
            }
            totals["with_evidence"] += is_populated and bool(entry.get("evidence_count"))
            bucket = per_field.setdefault(name, Counter())
            bucket[verdict] += 1
            bucket["populated"] += is_populated
            rows.append(
                {
                    "field": name,
                    "expected_state": state,
                    "verdict": verdict,
                    "populated": is_populated,
                    "required": required,
                    "needs_review": entry.get("needs_review"),
                    "evidence_count": entry.get("evidence_count", 0),
                    "evidence_assessment": copy.deepcopy(entry.get("evidence_assessment")),
                    "extraction_method": entry.get("extraction_method"),
                }
            )
        negatives = []
        for assertion in truth.get("negative_assertions", []):
            actual = fields.get(assertion["field"], {}).get("value")
            violated = populated(actual) and equal_value(
                assertion["must_not_equal"], actual, assertion["field"]
            )
            negatives.append({"field": assertion["field"], "violated": violated})
            totals["negative_violations"] += violated
        review = record.get("overall_status") == "REVIEW_REQUIRED" or any(
            r["needs_review"] for r in rows
        )
        totals["review_documents"] += review
        success = (
            predictions == expected_type
            and all(
                r["verdict"] in {"CORRECT", "CORRECTLY_ABSTAINED"} for r in rows if r["required"]
            )
            and not any(r["verdict"] == "INCORRECT" for r in rows)
        )
        totals["document_success"] += success
        expected_status = truth.get("expected_project_status")
        totals["false_needs_correction_evaluable"] += expected_status == "READY"
        profile_evaluable = record.get("project_status") is not None and any(
            r["required"] for r in rows
        )
        if expected_status is not None or profile_evaluable:
            totals["status_evaluable"] += 1
            required_unresolved = any(r["required"] and r["verdict"] != "CORRECT" for r in rows)
            unsafe_ready = record.get("project_status") == "READY" and (
                required_unresolved or (expected_status is not None and expected_status != "READY")
            )
            totals["false_ready"] += unsafe_ready
            totals["false_needs_correction"] += (
                expected_status == "READY" and record.get("project_status") == "NEEDS_CORRECTION"
            )
        if record.get("process_ms") is not None:
            durations.append(record["process_ms"])
        documents.append(
            {
                "sample_id": sid,
                "document_type": expected_type,
                "predicted_type": predictions,
                "processing_status": record.get("processing_status", "NOT_PROCESSED"),
                "document_status": record.get("overall_status"),
                "project_status": record.get("project_status"),
                "review_required": review,
                "fields": rows,
                "negative_assertions": negatives,
                "process_ms": record.get("process_ms"),
            }
        )

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    count = len(gold["samples"])
    return {
        "scorer_version": SCORER_VERSION,
        "dataset_version": gold["dataset_version"],
        "ground_truth_version": gold["gold_version"],
        "run_metadata": copy.deepcopy(run.get("metadata", {})),
        "counts": dict(totals),
        "metrics": {
            "SUPPORTED_FIELD_PRECISION": ratio(totals["CORRECT"], totals["populated"]),
            "SUPPORTED_FIELD_RECALL": ratio(totals["CORRECT"], totals["present_assertions"]),
            "WRONG_NON_NULL_COUNT": totals["INCORRECT"],
            "CORRECT_ABSTENTION_COUNT": totals["CORRECTLY_ABSTAINED"],
            "UNRESOLVED_REQUIRED_COUNT": totals["unresolved_required"],
            "EVIDENCE_COVERAGE": ratio(totals["with_evidence"], totals["populated"]),
            "CLASSIFICATION_ACCURACY": ratio(totals["classification_correct"], count),
            "CLASSIFICATION_ABSTENTION_RATE": ratio(totals["classification_abstained"], count),
            "DOCUMENT_SUCCESS_RATE": ratio(totals["document_success"], count),
            "REVIEW_RATE": ratio(totals["review_documents"], count),
            "FALSE_READY_COUNT": totals["false_ready"] if totals["status_evaluable"] else None,
            "FALSE_NEEDS_CORRECTION_COUNT": totals["false_needs_correction"]
            if totals["false_needs_correction_evaluable"]
            else None,
        },
        "per_field": {k: dict(v) for k, v in per_field.items()},
        "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
        "documents": documents,
        "latency_ms": {
            "median": statistics.median(durations) if durations else None,
            "min": min(durations) if durations else None,
            "max": max(durations) if durations else None,
        },
    }
