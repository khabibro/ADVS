"""Create a reproducible Phase 0 baseline from the existing evaluator.

This script deliberately composes the current gold-text and PaddleOCR runners
instead of redefining scoring logic. It adds metadata, dataset integrity, gap
analysis, and human/machine-readable reports around the existing metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_lib import paths
from eval_lib.runner import RunConfig, run_mock, run_paddle
from eval_lib.schema import GoldLabel

from app.core.config import get_settings
from app.document_intelligence.classification.classifier import CLASSIFIER_VERSION
from app.document_intelligence.extraction.base import EXTRACTOR_VERSION
from app.document_intelligence.validation.engine import VALIDATION_ENGINE_VERSION

BASELINE_SCHEMA_VERSION = "1.0"
DEFAULT_NAME = "baseline_v0"
FAST_PER_TYPE = 1


def _run(command: list[str], timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=paths.REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return "unknown"
    return (result.stdout or result.stderr).strip() or "unknown"


def _git_dirty() -> bool:
    return bool(_run(["git", "status", "--porcelain"]))


def _package_version(module_name: str) -> str | None:
    try:
        module = __import__(module_name)
    except Exception:
        return None
    return getattr(module, "__version__", None)


def _file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest_entries() -> list[dict[str, Any]]:
    return json.loads(paths.MANIFEST_PATH.read_text(encoding="utf-8"))["entries"]


def _gold_for(entry: dict[str, Any]) -> GoldLabel:
    return GoldLabel.from_json(
        json.loads((paths.REPO_ROOT / entry["gold_label_path"]).read_text(encoding="utf-8"))
    )


def _selected_fast_ids(entries: list[dict[str, Any]]) -> set[str]:
    selected: list[str] = []
    counts: Counter[str] = Counter()
    for entry in entries:
        doc_type = entry["document_type"]
        if counts[doc_type] < FAST_PER_TYPE:
            selected.append(entry["sample_id"])
            counts[doc_type] += 1
    return set(selected)


def _dataset_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    doc_types: Counter[str] = Counter()
    splits: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    source_classes: Counter[str] = Counter()
    validation_labels: Counter[str] = Counter()
    input_formats: Counter[str] = Counter()
    qualities: Counter[str] = Counter()
    layout_variants: Counter[str] = Counter()
    canonical_entries: list[dict[str, Any]] = []

    for entry in sorted(entries, key=lambda item: item["sample_id"]):
        gold = _gold_for(entry)
        doc_types[gold.document_type] += 1
        splits[gold.split] += 1
        sources[gold.source] += 1
        source_classes[gold.source_class] += 1
        input_formats[gold.input_format] += 1
        qualities[gold.quality] += 1
        layout_variants[gold.layout_variant] += 1
        validation_labels[gold.expected_validation_status or "NOT_AVAILABLE"] += 1
        rendered_path = paths.REPO_ROOT / entry["rendered_file_path"]
        gold_path = paths.REPO_ROOT / entry["gold_label_path"]
        text_path = paths.REPO_ROOT / entry["gold_text_path"] if entry.get("gold_text_path") else None
        canonical_entries.append(
            {
                "sample_id": entry["sample_id"],
                "source": entry["source"],
                "document_type": gold.document_type,
                "split": entry["split"],
                "source_class": gold.source_class,
                "input_format": gold.input_format,
                "quality": gold.quality,
                "layout_variant": gold.layout_variant,
                "expected_validation_status": gold.expected_validation_status,
                "gold_label_path": entry["gold_label_path"],
                "gold_label_sha256": _file_sha256(gold_path),
                "gold_text_path": entry.get("gold_text_path"),
                "gold_text_sha256": _file_sha256(text_path) if text_path else None,
                "rendered_file_path": entry["rendered_file_path"],
                "rendered_file_sha256": _file_sha256(rendered_path),
            }
        )

    canonical_blob = json.dumps(canonical_entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "count": len(entries),
        "fingerprint": hashlib.sha256(canonical_blob.encode("utf-8")).hexdigest(),
        "distribution": {
            "document_type": dict(sorted(doc_types.items())),
            "split": dict(sorted(splits.items())),
            "source": dict(sorted(sources.items())),
            "source_class": dict(sorted(source_classes.items())),
            "validation_label": dict(sorted(validation_labels.items())),
            "input_format": dict(sorted(input_formats.items())),
            "quality": dict(sorted(qualities.items())),
            "layout_variant": dict(sorted(layout_variants.items())),
        },
        "entries": canonical_entries,
    }


def _environment() -> dict[str, Any]:
    settings = get_settings()
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "git_commit": _run(["git", "rev-parse", "HEAD"]),
        "git_dirty": _git_dirty(),
        "python_version": platform.python_version(),
        "node_version": _run(["node", "--version"]),
        "operating_system": platform.platform(),
        "architecture": platform.machine(),
        "paddlepaddle_version": _package_version("paddle"),
        "paddleocr_version": _package_version("paddleocr"),
        "ocr_provider": settings.ocr_provider,
        "ocr_detection_model": settings.paddle_ocr_det_model_name,
        "ocr_recognition_model": settings.paddle_ocr_rec_model_name,
        "ocr_device": settings.paddle_ocr_device,
        "ocr_cache_dir": settings.paddle_ocr_cache_dir,
        "random_seed": 42,
        "classifier_version": CLASSIFIER_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "validation_engine_version": VALIDATION_ENGINE_VERSION,
    }


def _combine_gold(dev: dict[str, Any], held_out: dict[str, Any]) -> dict[str, Any]:
    samples = dev["samples"] + held_out["samples"]
    return {
        "mode": "gold_text",
        "splits": {"dev": dev, "held_out": held_out},
        "classification": _combine_classification(dev["classification"], held_out["classification"]),
        "extraction": _combine_extraction(dev["extraction"], held_out["extraction"]),
        "validation": _combine_validation(dev["validation"], held_out["validation"]),
        "failure_categories": _combine_failures(dev["failure_categories"], held_out["failure_categories"]),
        "samples": samples,
    }


def _combine_classification(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    total = left["total"] + right["total"]
    correct = left["correct"] + right["correct"]
    review_count = round(left["review_rate"] * left["total"]) + round(right["review_rate"] * right["total"])
    per_class: dict[str, Any] = {}
    for doc_type in sorted(set(left["per_class_accuracy"]) | set(right["per_class_accuracy"])):
        left_bucket = left["per_class_accuracy"].get(doc_type, {"correct": 0, "total": 0})
        right_bucket = right["per_class_accuracy"].get(doc_type, {"correct": 0, "total": 0})
        class_total = left_bucket["total"] + right_bucket["total"]
        class_correct = left_bucket["correct"] + right_bucket["correct"]
        per_class[doc_type] = {
            "correct": class_correct,
            "total": class_total,
            "accuracy": class_correct / class_total if class_total else 0.0,
        }
    return {
        "total": total,
        "correct": correct,
        "incorrect": total - correct,
        "accuracy": correct / total if total else 0.0,
        "review_rate": review_count / total if total else 0.0,
        "per_class_accuracy": per_class,
        "confusion_matrix": _merge_nested_counts(left["confusion_matrix"], right["confusion_matrix"]),
    }


def _combine_extraction(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    total = left["field_total"] + right["field_total"]
    correct = left["field_correct"] + right["field_correct"]
    missing = left["field_missing"] + right["field_missing"]
    false_value = left["field_false_value"] + right["field_false_value"]
    doc_total = left["document_level_total"] + right["document_level_total"]
    doc_success = left["document_level_success_count"] + right["document_level_success_count"]
    return {
        "field_total": total,
        "field_correct": correct,
        "field_missing": missing,
        "field_false_value": false_value,
        "field_accuracy": correct / total if total else 0.0,
        "missing_value_rate": missing / total if total else 0.0,
        "false_value_rate": false_value / total if total else 0.0,
        "per_field": _merge_metric_buckets(left["per_field"], right["per_field"]),
        "per_document_type": _merge_metric_buckets(left["per_document_type"], right["per_document_type"]),
        "document_level_success_count": doc_success,
        "document_level_total": doc_total,
        "document_level_success_rate": doc_success / doc_total if doc_total else 0.0,
    }


def _combine_validation(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    total = left["total"] + right["total"]
    correct = left["correct"] + right["correct"]
    false_ready_samples = left.get("false_ready_samples", left["false_pass_samples"]) + right.get(
        "false_ready_samples", right["false_pass_samples"]
    )
    false_needs_samples = left["false_needs_correction_samples"] + right["false_needs_correction_samples"]
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "confusion_matrix": _merge_nested_counts(left["confusion_matrix"], right["confusion_matrix"]),
        "false_ready_count": len(false_ready_samples),
        "false_ready_rate": len(false_ready_samples) / total if total else 0.0,
        "false_ready_samples": false_ready_samples,
        "false_pass_count": len(false_ready_samples),
        "false_pass_rate": len(false_ready_samples) / total if total else 0.0,
        "false_pass_samples": false_ready_samples,
        "false_needs_correction_count": len(false_needs_samples),
        "false_needs_correction_samples": false_needs_samples,
    }


def _combine_failures(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for payload in (left, right):
        for category, bucket in payload.get("by_category", {}).items():
            counts[category] += bucket["count"]
    total = sum(counts.values())
    return {
        "total_failing_samples": total,
        "by_category": {
            name: {"count": count, "pct": count / total if total else 0.0}
            for name, count in counts.most_common()
        },
    }


def _merge_metric_buckets(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in sorted(set(left) | set(right)):
        bucket = Counter(left.get(key, {}))
        bucket.update(right.get(key, {}))
        merged[key] = dict(bucket)
        if "correct" in merged[key] and "total" in merged[key]:
            total = merged[key]["total"]
            merged[key]["accuracy"] = merged[key]["correct"] / total if total else 0.0
    return merged


def _merge_nested_counts(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Counter[str]] = defaultdict(Counter)
    for payload in (left, right):
        for row_key, row in payload.items():
            merged[row_key].update(row)
    return {row_key: dict(counter) for row_key, counter in sorted(merged.items())}


def _gap_analysis(gold: dict[str, Any], paddle: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for field_name in sorted(set(gold["extraction"]["per_field"]) | set(paddle["extraction"]["per_field"])):
        g = gold["extraction"]["per_field"].get(field_name, {})
        p = paddle["extraction"]["per_field"].get(field_name, {})
        gold_acc = g.get("correct", 0) / g.get("total", 1) if g.get("total") else None
        paddle_acc = p.get("correct", 0) / p.get("total", 1) if p.get("total") else None
        fields[field_name] = {
            "gold_accuracy": gold_acc,
            "paddle_accuracy": paddle_acc,
            "gap": (gold_acc - paddle_acc) if gold_acc is not None and paddle_acc is not None else None,
            "gold": g,
            "paddle": p,
        }
    by_document_type: dict[str, Any] = {}
    for doc_type in sorted(
        set(gold["extraction"]["per_document_type"]) | set(paddle["extraction"]["per_document_type"])
    ):
        g = gold["extraction"]["per_document_type"].get(doc_type, {})
        p = paddle["extraction"]["per_document_type"].get(doc_type, {})
        gold_acc = g.get("fields_correct", 0) / g.get("fields_total", 1) if g.get("fields_total") else None
        paddle_acc = p.get("fields_correct", 0) / p.get("fields_total", 1) if p.get("fields_total") else None
        by_document_type[doc_type] = {
            "gold_field_accuracy": gold_acc,
            "paddle_field_accuracy": paddle_acc,
            "gap": (gold_acc - paddle_acc) if gold_acc is not None and paddle_acc is not None else None,
            "gold": g,
            "paddle": p,
        }
    return {
        "field_accuracy_gap": gold["extraction"]["field_accuracy"] - paddle["extraction"]["field_accuracy"],
        "document_success_gap": gold["extraction"]["document_level_success_rate"]
        - paddle["extraction"]["document_level_success_rate"],
        "validation_accuracy_gap": gold["validation"]["accuracy"] - paddle["validation"]["accuracy"],
        "by_field": fields,
        "by_document_type": by_document_type,
    }


def _sample_failure_examples(payload: dict[str, Any], limit: int = 5) -> dict[str, list[str]]:
    examples: dict[str, list[str]] = defaultdict(list)
    for sample in payload.get("samples", []):
        category = sample.get("failure_category")
        if category and len(examples[category]) < limit:
            examples[category].append(sample["sample_id"])
    return dict(sorted(examples.items()))


def _performance(started: float, gold: dict[str, Any], paddle: dict[str, Any]) -> dict[str, Any]:
    total_seconds = time.perf_counter() - started
    docs = gold["classification"]["total"] + paddle["classification"]["total"]
    return {
        "total_seconds": total_seconds,
        "documents_processed": docs,
        "average_seconds_per_document": total_seconds / docs if docs else None,
        "note": "Gold/Paddle sample processing_ms is downstream scorer time; total_seconds is wall-clock baseline runtime including OCR.",
    }


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _pct(value: float | None) -> str:
    return "NOT AVAILABLE" if value is None else f"{value:.2%}"


def _write_markdown(payload: dict[str, Any], path: Path) -> None:
    gold = payload["gold_text"]
    paddle = payload["paddleocr"]
    dataset = payload["dataset"]
    gap = payload["gap_analysis"]
    lines = [
        "# ADVS Baseline",
        "",
        "## Environment",
        f"- Baseline: `{payload['metadata']['baseline_name']}`",
        f"- Git commit: `{payload['metadata']['git_commit']}`",
        f"- Git dirty: `{payload['metadata']['git_dirty']}`",
        f"- Python: `{payload['metadata']['python_version']}`",
        f"- Node: `{payload['metadata']['node_version']}`",
        f"- PaddlePaddle: `{payload['metadata']['paddlepaddle_version']}`",
        f"- PaddleOCR: `{payload['metadata']['paddleocr_version']}`",
        f"- OCR provider/device: `{payload['metadata']['ocr_provider']}` / `{payload['metadata']['ocr_device']}`",
        f"- Models: `{payload['metadata']['ocr_detection_model']}`, `{payload['metadata']['ocr_recognition_model']}`",
        "",
        "## Dataset",
        f"- Count: `{dataset['count']}`",
        f"- Fingerprint: `{dataset['fingerprint']}`",
        f"- Document types: `{dataset['distribution']['document_type']}`",
        f"- Splits: `{dataset['distribution']['split']}`",
        f"- Source classes: `{dataset['distribution']['source_class']}`",
        f"- Validation labels: `{dataset['distribution']['validation_label']}`",
        "",
        "## Gold Text",
        f"- Classification accuracy: {_pct(gold['classification']['accuracy'])}",
        f"- Field accuracy: {_pct(gold['extraction']['field_accuracy'])}",
        f"- Document-level extraction success: {_pct(gold['extraction']['document_level_success_rate'])}",
        f"- Validation accuracy: {_pct(gold['validation']['accuracy'])}",
        f"- False READY: `{gold['validation']['false_ready_count']}` / `{gold['validation']['total']}`",
        "",
        "## Real PaddleOCR",
        f"- OCR attempts: `{paddle['ocr_stats']['attempted']}`",
        f"- OCR succeeded: `{paddle['ocr_stats']['succeeded']}`",
        f"- OCR failed: `{paddle['ocr_stats']['failed']}`",
        f"- OCR empty: `{paddle['ocr_stats']['empty']}`",
        f"- CER mean: `{paddle['ocr_text_metrics']['cer_mean']}`",
        f"- Text similarity mean: `{paddle['ocr_text_metrics']['similarity_mean']}`",
        f"- Classification accuracy: {_pct(paddle['classification']['accuracy'])}",
        f"- Field accuracy: {_pct(paddle['extraction']['field_accuracy'])}",
        f"- Document-level extraction success: {_pct(paddle['extraction']['document_level_success_rate'])}",
        f"- Validation accuracy: {_pct(paddle['validation']['accuracy'])}",
        f"- False READY: `{paddle['validation']['false_ready_count']}` / `{paddle['validation']['total']}`",
        "",
        "## Gold vs OCR Gap",
        f"- Field accuracy gap: {_pct(gap['field_accuracy_gap'])}",
        f"- Document success gap: {_pct(gap['document_success_gap'])}",
        f"- Validation accuracy gap: {_pct(gap['validation_accuracy_gap'])}",
        "",
        "| Field | Gold | PaddleOCR | Gap |",
        "|---|---:|---:|---:|",
    ]
    for field_name, stats in sorted(
        gap["by_field"].items(), key=lambda item: item[1]["gap"] if item[1]["gap"] is not None else -1, reverse=True
    ):
        lines.append(
            f"| {field_name} | {_pct(stats['gold_accuracy'])} | {_pct(stats['paddle_accuracy'])} | {_pct(stats['gap'])} |"
        )
    lines.extend(
        [
            "",
            "## Failure Categories",
            "",
            "### Gold Text",
            json.dumps(gold["failure_categories"], ensure_ascii=False, indent=2),
            "",
            "### PaddleOCR",
            json.dumps(paddle["failure_categories"], ensure_ascii=False, indent=2),
            "",
            "## Safety",
            f"- Gold false READY samples: `{gold['validation']['false_ready_samples']}`",
            f"- Paddle false READY samples: `{paddle['validation']['false_ready_samples']}`",
            "",
            "## Performance",
            f"- Total runtime seconds: `{payload['performance']['total_seconds']:.3f}`",
            f"- Documents processed: `{payload['performance']['documents_processed']}`",
            f"- Average seconds per document: `{payload['performance']['average_seconds_per_document']:.3f}`",
            "",
            "## Known Limitations",
            "- REAL OCR EVALUATION: NOT YET AVAILABLE.",
            "- Synthetic/recreated rendered samples are development evidence only.",
            "- Sample-level results omit field values and raw OCR text to avoid unnecessary sensitive text storage.",
            "",
            "## Reproduction Command",
            f"- `{payload['reproduction_command']}`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_baseline(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    all_entries = _load_manifest_entries()
    sample_ids = _selected_fast_ids(all_entries) if args.fast else None
    entries = [entry for entry in all_entries if sample_ids is None or entry["sample_id"] in sample_ids]
    name = args.name or (f"{DEFAULT_NAME}_fast" if args.fast else DEFAULT_NAME)

    dev = run_mock(RunConfig("mock", "dev", f"{name}_gold_dev", sample_ids=sample_ids))
    held_out = run_mock(RunConfig("mock", "held_out", f"{name}_gold_held_out", sample_ids=sample_ids))
    paddle = run_paddle(RunConfig("paddle", None, f"{name}_paddle", sample_ids=sample_ids))
    gold = _combine_gold(dev, held_out)

    payload = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "metadata": {"baseline_name": name, **_environment()},
        "dataset": _dataset_summary(entries),
        "gold_text": gold,
        "paddleocr": paddle,
        "gap_analysis": _gap_analysis(gold, paddle),
        "failure_examples": {
            "gold_text": _sample_failure_examples(gold),
            "paddleocr": _sample_failure_examples(paddle),
        },
        "performance": _performance(started, gold, paddle),
        "metric_definitions": {
            "ocr_cer": "Levenshtein distance over whitespace-stripped gold OCR text divided by gold character count.",
            "ocr_text_similarity": "difflib SequenceMatcher ratio over whitespace-stripped gold OCR text and OCR text.",
            "classification_accuracy": "Samples with predicted document_type equal to gold document_type divided by scored samples.",
            "field_accuracy": "Required fields with normalized predicted value exactly equal to normalized gold value divided by required fields.",
            "document_level_success": "Supported-document samples where every required field is correct divided by supported-document samples.",
            "validation_accuracy": "Samples with predicted validation status equal to gold validation status divided by validation-labeled samples.",
            "false_ready_count": "Validation-labeled samples where gold status is not READY but predicted status is READY.",
            "false_ready_rate": "false_ready_count divided by validation-labeled samples.",
            "review_rate": "Classification needs_review count divided by scored samples.",
        },
        "reproduction_command": "make baseline-fast" if args.fast else "make baseline",
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a reproducible ADVS baseline report.")
    parser.add_argument("--name", default=None)
    parser.add_argument("--fast", action="store_true", help="Use a deterministic one-sample-per-type subset.")
    args = parser.parse_args()

    payload = build_baseline(args)
    name = payload["metadata"]["baseline_name"]
    baseline_dir = paths.EVAL_ROOT / "baselines"
    results_json = paths.RESULTS_DIR / f"{name}.json"
    baseline_json = baseline_dir / f"{name}.json"
    baseline_md = baseline_dir / f"{name}.md"
    _write_json(payload, results_json)
    _write_json(payload, baseline_json)
    _write_markdown(payload, baseline_md)
    print(f"Baseline JSON written to {results_json.relative_to(paths.REPO_ROOT)}")
    print(f"Baseline snapshot written to {baseline_json.relative_to(paths.REPO_ROOT)}")
    print(f"Baseline report written to {baseline_md.relative_to(paths.REPO_ROOT)}")
    print(f"Dataset fingerprint: {payload['dataset']['fingerprint']}")
    print(f"Gold field accuracy: {payload['gold_text']['extraction']['field_accuracy']:.2%}")
    print(f"Paddle field accuracy: {payload['paddleocr']['extraction']['field_accuracy']:.2%}")
    print(f"Paddle false READY: {payload['paddleocr']['validation']['false_ready_count']}")


if __name__ == "__main__":
    main()
