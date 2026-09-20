"""Metric computation over a list of per-sample evaluation results.

Kept separate from the runner (which produces SampleResult objects) so the
comparison logic is independently testable and reusable by both the
mock-mode and OCR-mode runners.
"""

from dataclasses import dataclass

CLASSIFICATION_TYPES = [
    "GRADUATION_CERTIFICATE",
    "CAREER_CERTIFICATE",
    "BUSINESS_REGISTRATION_CERTIFICATE",
    "SME_CONFIRMATION_CERTIFICATE",
    "UNKNOWN",
]
CANONICAL_VALIDATION_STATUSES = ["READY", "REVIEW_REQUIRED", "NEEDS_CORRECTION"]
LEGACY_VALIDATION_STATUS_MAP = {
    "PASS": "READY",
    "REVIEW": "REVIEW_REQUIRED",
    "READY": "READY",
    "REVIEW_REQUIRED": "REVIEW_REQUIRED",
    "NEEDS_CORRECTION": "NEEDS_CORRECTION",
}


@dataclass
class FieldResult:
    field_name: str
    gold_value: str | None
    predicted_value: str | None
    status: str  # correct | missing | false_value


@dataclass
class SampleResult:
    sample_id: str
    source: str
    split: str
    document_type_gold: str
    document_type_pred: str
    classification_score: float
    classification_confidence: float
    classification_needs_review: bool
    field_results: list[FieldResult]
    validation_gold: str | None
    validation_pred: str | None
    failure_category: str | None
    failure_reason: str
    processing_ms: float
    layout_variant: str = ""
    quality: str = ""
    input_format: str = ""
    notes: str = ""

    @property
    def classification_correct(self) -> bool:
        return self.document_type_gold == self.document_type_pred

    @property
    def required_fields_total(self) -> int:
        return len(self.field_results)

    @property
    def required_fields_correct(self) -> int:
        return sum(1 for f in self.field_results if f.status == "correct")

    @property
    def document_level_extraction_success(self) -> bool:
        return all(f.status == "correct" for f in self.field_results)

    @property
    def validation_correct(self) -> bool | None:
        if self.validation_gold is None:
            return None
        return canonical_validation_status(self.validation_gold) == canonical_validation_status(
            self.validation_pred
        )


def canonical_validation_status(value: str | None) -> str | None:
    if value is None:
        return None
    return LEGACY_VALIDATION_STATUS_MAP.get(value, value)


def compare_fields(
    gold: dict[str, str | None], predicted: dict[str, str | None]
) -> list[FieldResult]:
    results = []
    for name, gold_value in gold.items():
        predicted_value = predicted.get(name)
        if gold_value == predicted_value:
            status = "correct"
        elif predicted_value is None:
            status = "missing"
        else:
            status = "false_value"
        results.append(FieldResult(name, gold_value, predicted_value, status))
    return results


def classification_metrics(samples: list[SampleResult]) -> dict:
    scored = [s for s in samples]
    total = len(scored)
    correct = sum(1 for s in scored if s.classification_correct)
    unknown_pred = sum(1 for s in scored if s.document_type_pred == "UNKNOWN")
    review = sum(1 for s in scored if s.classification_needs_review)

    confusion: dict[str, dict[str, int]] = {
        g: dict.fromkeys(CLASSIFICATION_TYPES, 0) for g in CLASSIFICATION_TYPES
    }
    per_class: dict[str, dict[str, int]] = {}
    for s in scored:
        confusion.setdefault(s.document_type_gold, dict.fromkeys(CLASSIFICATION_TYPES, 0))
        confusion[s.document_type_gold][s.document_type_pred] = (
            confusion[s.document_type_gold].get(s.document_type_pred, 0) + 1
        )
        bucket = per_class.setdefault(s.document_type_gold, {"total": 0, "correct": 0})
        bucket["total"] += 1
        if s.classification_correct:
            bucket["correct"] += 1

    correct_scores = [s.classification_score for s in scored if s.classification_correct]
    incorrect_scores = [s.classification_score for s in scored if not s.classification_correct]

    return {
        "total": total,
        "correct": correct,
        "incorrect": total - correct,
        "unknown_predicted": unknown_pred,
        "review_rate": review / total if total else 0.0,
        "accuracy": correct / total if total else 0.0,
        "per_class_accuracy": {
            k: {
                "correct": v["correct"],
                "total": v["total"],
                "accuracy": v["correct"] / v["total"] if v["total"] else 0.0,
            }
            for k, v in per_class.items()
        },
        "confusion_matrix": confusion,
        "confidence_analysis": {
            "correct_score_mean": _mean(correct_scores),
            "incorrect_score_mean": _mean(incorrect_scores),
            "correct_count": len(correct_scores),
            "incorrect_count": len(incorrect_scores),
        },
    }


def extraction_metrics(samples: list[SampleResult]) -> dict:
    scored = [s for s in samples if s.document_type_gold != "UNKNOWN"]
    field_total = field_correct = field_missing = field_false = 0
    per_field: dict[str, dict[str, int]] = {}
    per_type: dict[str, dict[str, int]] = {}
    doc_success = 0

    for s in scored:
        per_type_bucket = per_type.setdefault(
            s.document_type_gold,
            {"documents": 0, "documents_all_correct": 0, "fields_total": 0, "fields_correct": 0},
        )
        per_type_bucket["documents"] += 1
        per_type_bucket["fields_total"] += s.required_fields_total
        per_type_bucket["fields_correct"] += s.required_fields_correct
        if s.document_level_extraction_success:
            doc_success += 1
            per_type_bucket["documents_all_correct"] += 1
        for f in s.field_results:
            field_total += 1
            bucket = per_field.setdefault(
                f.field_name, {"correct": 0, "missing": 0, "false_value": 0, "total": 0}
            )
            bucket["total"] += 1
            bucket[f.status] += 1
            if f.status == "correct":
                field_correct += 1
            elif f.status == "missing":
                field_missing += 1
            else:
                field_false += 1

    return {
        "field_total": field_total,
        "field_correct": field_correct,
        "field_missing": field_missing,
        "field_false_value": field_false,
        "field_accuracy": field_correct / field_total if field_total else 0.0,
        "missing_value_rate": field_missing / field_total if field_total else 0.0,
        "false_value_rate": field_false / field_total if field_total else 0.0,
        "per_field": per_field,
        "per_document_type": per_type,
        "document_level_success_count": doc_success,
        "document_level_total": len(scored),
        "document_level_success_rate": doc_success / len(scored) if scored else 0.0,
    }


def validation_metrics(samples: list[SampleResult]) -> dict:
    scored = [s for s in samples if s.validation_gold is not None]
    total = len(scored)
    correct = sum(1 for s in scored if s.validation_correct)
    confusion: dict[str, dict[str, int]] = {
        g: dict.fromkeys(CANONICAL_VALIDATION_STATUSES, 0) for g in CANONICAL_VALIDATION_STATUSES
    }
    false_ready = []
    false_needs_correction = []
    for s in scored:
        gold_status = canonical_validation_status(s.validation_gold) or "UNKNOWN"
        pred_status = canonical_validation_status(s.validation_pred) or "UNKNOWN"
        confusion.setdefault(gold_status, dict.fromkeys(CANONICAL_VALIDATION_STATUSES, 0))
        confusion[gold_status][pred_status] = confusion[gold_status].get(pred_status, 0) + 1
        if gold_status != "READY" and pred_status == "READY":
            false_ready.append(s.sample_id)
        if gold_status == "READY" and pred_status == "NEEDS_CORRECTION":
            false_needs_correction.append(s.sample_id)

    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "confusion_matrix": confusion,
        "false_ready_count": len(false_ready),
        "false_ready_samples": false_ready,
        "false_pass_count": len(false_ready),
        "false_pass_samples": false_ready,
        "false_needs_correction_count": len(false_needs_correction),
        "false_needs_correction_samples": false_needs_correction,
    }


def failure_category_breakdown(samples: list[SampleResult]) -> dict:
    counts: dict[str, int] = {}
    for s in samples:
        if s.failure_category:
            counts[s.failure_category] = counts.get(s.failure_category, 0) + 1
    total_failures = sum(counts.values())
    return {
        "total_failing_samples": total_failures,
        "by_category": {
            k: {"count": v, "pct": v / total_failures if total_failures else 0.0}
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
        },
    }


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None
