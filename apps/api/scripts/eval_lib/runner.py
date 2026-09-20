"""Evaluation runner.

Mode A ("mock", default): scores classification/extraction/validation
against each sample's gold OCR text directly. It isolates downstream
heuristics and does not measure OCR accuracy.

Mode B ("paddle"): runs each renderable sample through PaddleOCR, assembles
the recognized text the same way production does, and scores the downstream
pipeline. Real samples are only scored if their gold label has been
human-verified (`verified: true`) -- an unverified label is never treated
as ground truth.
"""

import json
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher

from eval_lib import paths
from eval_lib.metrics import (
    FieldResult,
    SampleResult,
    classification_metrics,
    compare_fields,
    extraction_metrics,
    failure_category_breakdown,
    validation_metrics,
)
from eval_lib.schema import GoldLabel
from eval_lib.submissions import SubmissionBundle, build_bundles

from app.core.config import get_settings
from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import (
    CLASSIFIER_VERSION,
    ClassificationResult,
    DocumentClassifier,
)
from app.document_intelligence.extraction.base import EXTRACTOR_VERSION
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.providers import OCRProvider, PaddleOCRProvider
from app.document_intelligence.validation.engine import VALIDATION_ENGINE_VERSION, ValidationEngine

_MIME_BY_EXT = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg"}


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=paths.REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def load_manifest_entries(split: str | None, sample_ids: set[str] | None = None) -> list[dict]:
    manifest = json.loads(paths.MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = manifest["entries"]
    if split:
        entries = [e for e in entries if e["split"] == split]
    if sample_ids:
        entries = [e for e in entries if e["sample_id"] in sample_ids]
    return entries


def _categorize_failure(
    gold: GoldLabel,
    document_type_correct: bool,
    field_results: list[FieldResult],
    validation_gold: str | None,
    validation_pred: str | None,
) -> tuple[str | None, str]:
    if not document_type_correct:
        if "ambiguous" in gold.notes or "near-miss" in gold.notes:
            return (
                "AMBIGUOUS_DOCUMENT",
                "Deliberately ambiguous/near-miss negative example; forcing a supported "
                "type here would be the real error, not this UNKNOWN/mismatch.",
            )
        return "CLASSIFICATION_ERROR", "Predicted document_type differs from gold."

    wrong_fields = [f for f in field_results if f.status != "correct"]
    if wrong_fields:
        names = ", ".join(f.field_name for f in wrong_fields)
        if "multiple employment periods" in gold.notes:
            return (
                "UNSUPPORTED_LAYOUT",
                f"Multiple employment periods present (documented single-period limitation). Fields: {names}",
            )
        if gold.layout_variant in ("vertical", "compact"):
            return (
                "EXTRACTION_PATTERN_ERROR",
                f"Layout '{gold.layout_variant}' separates label/value across lines or packs "
                f"multiple pairs onto one line, which the same-line label-match pattern does not "
                f"support. Fields: {names}",
            )
        if "label spacing variant applied" in gold.notes:
            return (
                "EXTRACTION_LABEL_ERROR",
                f"A label was rendered with an internal whitespace variant not recognized by "
                f"exact label matching. Fields: {names}",
            )
        return "EXTRACTION_LABEL_ERROR", f"Field(s) not matched as expected: {names}"

    if validation_gold is not None and validation_gold != validation_pred:
        return (
            "VALIDATION_RULE_ERROR",
            f"Validation status gold={validation_gold} pred={validation_pred} despite correct "
            f"classification/extraction.",
        )
    return None, ""


@dataclass
class Pipeline:
    classifier: DocumentClassifier
    registry: ExtractorRegistry
    validator: ValidationEngine


def _score_text(gold: GoldLabel, text: str, pipeline: Pipeline) -> SampleResult:
    started = time.perf_counter()
    classification: ClassificationResult = pipeline.classifier.classify(text)
    predicted_type = DocumentType(classification.predicted_type)
    extracted = pipeline.registry.extract(predicted_type, text)
    predicted_fields = {f.field_name: f.normalized_value for f in extracted}
    gold_fields = {name: f.value for name, f in gold.fields.items()}
    field_results = compare_fields(gold_fields, predicted_fields)

    validation_pred = None
    if gold.expected_validation_status is not None:
        issues = pipeline.validator.validate_document(
            None, predicted_type, extracted, None, None, False, None
        )
        validation_pred = str(pipeline.validator.overall_status(issues))
    elapsed_ms = (time.perf_counter() - started) * 1000

    classification_correct = classification.predicted_type == gold.document_type
    category, reason = _categorize_failure(
        gold,
        classification_correct,
        field_results,
        gold.expected_validation_status,
        validation_pred,
    )

    return SampleResult(
        sample_id=gold.sample_id,
        source=gold.source,
        split=gold.split,
        document_type_gold=gold.document_type,
        document_type_pred=str(classification.predicted_type),
        classification_score=classification.score,
        classification_confidence=classification.confidence_score,
        classification_needs_review=classification.needs_review,
        field_results=field_results,
        validation_gold=gold.expected_validation_status,
        validation_pred=validation_pred,
        failure_category=category,
        failure_reason=reason,
        processing_ms=elapsed_ms,
        layout_variant=gold.layout_variant,
        quality=gold.quality,
        input_format=gold.input_format,
        notes=gold.notes,
    )


@dataclass
class RunConfig:
    mode: str  # "mock" | "paddle"
    split: str | None
    output_name: str
    source_class: str | None = None  # filter, e.g. "RECREATED_FROM_PUBLIC_REFERENCE"
    sample_ids: set[str] | None = None


def run_mock(config: RunConfig) -> dict:
    pipeline = Pipeline(DocumentClassifier(), ExtractorRegistry(), ValidationEngine())
    entries = load_manifest_entries(config.split, config.sample_ids)
    samples: list[SampleResult] = []
    skipped_unverified = 0

    for entry in entries:
        gold = GoldLabel.from_json(
            json.loads((paths.REPO_ROOT / entry["gold_label_path"]).read_text(encoding="utf-8"))
        )
        if config.source_class and gold.source_class != config.source_class:
            continue
        if not gold.verified:
            skipped_unverified += 1
            continue
        if not entry.get("gold_text_path"):
            # Real samples without a manual text transcription can only be
            # scored via OCR mode after their label is verified.
            skipped_unverified += 1
            continue
        text = (paths.REPO_ROOT / entry["gold_text_path"]).read_text(encoding="utf-8")
        samples.append(_score_text(gold, text, pipeline))

    payload = _build_result_payload(config, samples)
    payload["skipped_unverified_or_no_gold_text"] = skipped_unverified
    return payload


def run_paddle(config: RunConfig) -> dict:
    settings = get_settings()
    return _run_ocr_provider(config, PaddleOCRProvider(settings), "paddle")


def _run_ocr_provider(
    config: RunConfig,
    provider: OCRProvider,
    provider_name: str,
) -> dict:
    entries = load_manifest_entries(config.split, config.sample_ids)

    pipeline = Pipeline(DocumentClassifier(), ExtractorRegistry(), ValidationEngine())
    ocr_stats = {"attempted": 0, "succeeded": 0, "failed": 0, "empty": 0}
    ocr_text_results: list[dict] = []
    samples: list[SampleResult] = []
    skipped_unverified = 0

    import asyncio

    async def _run() -> None:
        nonlocal skipped_unverified
        for entry in entries:
            gold = GoldLabel.from_json(
                json.loads((paths.REPO_ROOT / entry["gold_label_path"]).read_text(encoding="utf-8"))
            )
            if config.source_class and gold.source_class != config.source_class:
                continue
            file_path = paths.REPO_ROOT / entry["rendered_file_path"]
            ocr_stats["attempted"] += 1
            try:
                mime = _MIME_BY_EXT[file_path.suffix.strip(".")]
                pages = await provider.extract_document(file_path, mime, file_path.name)
            except Exception:
                ocr_stats["failed"] += 1
                continue
            ocr_stats["succeeded"] += 1
            if not any(p.text.strip() for p in pages):
                ocr_stats["empty"] += 1
            if gold.verified:
                ocr_text = "\n\n".join(p.text for p in pages if p.text)
                samples.append(_score_text(gold, ocr_text, pipeline))
                if entry.get("gold_text_path"):
                    gold_text = (paths.REPO_ROOT / entry["gold_text_path"]).read_text(
                        encoding="utf-8"
                    )
                    ocr_text_results.append(_ocr_text_metrics(gold.sample_id, gold_text, ocr_text))
            else:
                skipped_unverified += 1

    asyncio.run(_run())
    payload = _build_result_payload(config, samples)
    payload["ocr_stats"] = ocr_stats
    payload["ocr_text_metrics"] = _aggregate_ocr_text_metrics(ocr_text_results)
    payload["skipped_unverified_or_no_gold_text"] = skipped_unverified
    payload["status"] = "RUN" if ocr_stats["succeeded"] else "NOT_RUN"
    if not ocr_stats["succeeded"]:
        payload["reason"] = f"{provider_name}_provider_unavailable_or_all_samples_failed"
    return payload


def _normalize_for_ocr_metric(text: str) -> str:
    return "".join(text.split())


def _ocr_text_metrics(sample_id: str, gold_text: str, ocr_text: str) -> dict:
    gold_norm = _normalize_for_ocr_metric(gold_text)
    ocr_norm = _normalize_for_ocr_metric(ocr_text)
    distance = _levenshtein(gold_norm, ocr_norm)
    denom = len(gold_norm) or 1
    return {
        "sample_id": sample_id,
        "cer": distance / denom,
        "similarity": SequenceMatcher(None, gold_norm, ocr_norm).ratio(),
    }


def _aggregate_ocr_text_metrics(results: list[dict]) -> dict:
    if not results:
        return {"total": 0, "cer_mean": None, "similarity_mean": None}
    return {
        "total": len(results),
        "cer_mean": sum(r["cer"] for r in results) / len(results),
        "similarity_mean": sum(r["similarity"] for r in results) / len(results),
        "samples": results,
    }


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _sample_id_to_entry() -> dict[str, dict]:
    return {e["sample_id"]: e for e in load_manifest_entries(None)}


def _score_bundle(
    bundle: SubmissionBundle, pipeline: Pipeline, entry_by_id: dict[str, dict]
) -> dict:
    seen: set[str] = set()
    all_issues = []
    document_predictions: list[dict] = []
    predicted_types: set[str] = set()

    for sample_id in bundle.document_sample_ids:
        entry = entry_by_id[sample_id]
        text = (paths.REPO_ROOT / entry["gold_text_path"]).read_text(encoding="utf-8")
        classification = pipeline.classifier.classify(text)
        predicted_type = DocumentType(classification.predicted_type)
        extracted = pipeline.registry.extract(predicted_type, text)

        duplicate = sample_id in seen
        seen.add(sample_id)

        issues = pipeline.validator.validate_document(
            None,
            predicted_type,
            extracted,
            bundle.applicant_name,
            bundle.company_name,
            duplicate,
            None,
        )
        all_issues.extend(issues)
        predicted_types.add(str(predicted_type))
        document_predictions.append(
            {
                "sample_id": sample_id,
                "document_type_pred": str(predicted_type),
                "duplicate_flagged": duplicate,
            }
        )

    required_issues = pipeline.validator.validate_required_documents(
        [DocumentType(t) for t in bundle.required_document_types],
        {DocumentType(t) for t in predicted_types},
    )
    all_issues.extend(required_issues)

    predicted_status = str(pipeline.validator.overall_status(all_issues))
    return {
        "bundle_id": bundle.bundle_id,
        "description": bundle.description,
        "expected_status": bundle.expected_status,
        "predicted_status": predicted_status,
        "correct": predicted_status == bundle.expected_status,
        "reason": bundle.reason,
        "documents": document_predictions,
        "issue_codes": [i.code for i in all_issues],
    }


def run_submissions() -> dict:
    pipeline = Pipeline(DocumentClassifier(), ExtractorRegistry(), ValidationEngine())
    entry_by_id = _sample_id_to_entry()
    bundles = build_bundles()
    results = [_score_bundle(bundle, pipeline, entry_by_id) for bundle in bundles]

    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    confusion: dict[str, dict[str, int]] = {}
    for r in results:
        confusion.setdefault(r["expected_status"], {}).setdefault(r["predicted_status"], 0)
        confusion[r["expected_status"]][r["predicted_status"]] += 1

    return {
        "reproducibility": {
            "evaluated_at": datetime.now(UTC).isoformat(),
            "git_commit": _git_commit(),
            "classifier_version": CLASSIFIER_VERSION,
            "extractor_version": EXTRACTOR_VERSION,
            "validation_engine_version": VALIDATION_ENGINE_VERSION,
            "mode": "mock",
            "bundle_count": total,
        },
        "summary": {
            "total": total,
            "correct": correct,
            "incorrect": total - correct,
            "accuracy": correct / total if total else 0.0,
            "confusion_matrix": confusion,
        },
        "bundles": results,
    }


def _build_result_payload(config: RunConfig, samples: list[SampleResult]) -> dict:
    return {
        "reproducibility": {
            "evaluated_at": datetime.now(UTC).isoformat(),
            "git_commit": _git_commit(),
            "classifier_version": CLASSIFIER_VERSION,
            "extractor_version": EXTRACTOR_VERSION,
            "validation_engine_version": VALIDATION_ENGINE_VERSION,
            "mode": config.mode,
            "split": config.split or "all",
            "sample_count": len(samples),
        },
        "classification": classification_metrics(samples),
        "extraction": extraction_metrics(samples),
        "validation": validation_metrics(samples),
        "failure_categories": failure_category_breakdown(samples),
        "samples": [_sample_to_json(s) for s in samples],
    }


def _sample_to_json(s: SampleResult) -> dict:
    return {
        "sample_id": s.sample_id,
        "source": s.source,
        "split": s.split,
        "document_type_gold": s.document_type_gold,
        "document_type_pred": s.document_type_pred,
        "classification_correct": s.classification_correct,
        "classification_score": s.classification_score,
        "classification_confidence": s.classification_confidence,
        "classification_needs_review": s.classification_needs_review,
        "required_fields_correct": s.required_fields_correct,
        "required_fields_total": s.required_fields_total,
        "document_level_extraction_success": s.document_level_extraction_success,
        "validation_gold": s.validation_gold,
        "validation_pred": s.validation_pred,
        "validation_correct": s.validation_correct,
        "failure_category": s.failure_category,
        "failure_reason": s.failure_reason,
        "processing_ms": round(s.processing_ms, 3),
        "layout_variant": s.layout_variant,
        "quality": s.quality,
        "input_format": s.input_format,
        "notes": s.notes,
        "fields": [
            {"field_name": f.field_name, "status": f.status}  # values omitted from shareable JSON
            for f in s.field_results
        ],
    }
