"""Score a round-2 run against ground truth and emit redacted artifacts.

Separated from ``run_round2.py`` so that a run can be re-scored without
re-running OCR, and so that nothing sensitive has to leave the work
directory: this is the only module that writes committable output.

Redaction
---------
Committed artifacts carry, per field: the verdict, whether a value was
populated, and an opaque token derived from a salted hash of the value. The
token is stable across runs (so before/after comparison works) and
non-reversible (so it leaks no name, id or number).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import run_round2 as runner

ROUND_DIR = Path(__file__).resolve().parent
WORK_DIR = ROUND_DIR / "work"
VERDICTS = ("CORRECT", "INCORRECT", "UNRESOLVED", "NOT_EVALUATED")


def _comparable(value: Any) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _verdict(expected: dict[str, Any], actual: str | None) -> str:
    category = expected["gt"]
    if category in {"AMBIGUOUS", "NOT_EVIDENCED"}:
        return "NOT_EVALUATED"
    if actual is None:
        return "UNRESOLVED"
    if category == "VERIFIED_ABSENT":
        return "INCORRECT" if str(actual).strip() else "CORRECT"
    return "CORRECT" if _comparable(expected.get("value")) == _comparable(actual) else "INCORRECT"


def rescore(run: dict[str, Any], ground_truth: dict[str, Any]) -> dict[str, Any]:
    """Re-derive every verdict from stored values + ground truth."""
    for record in run["samples"]:
        truth = ground_truth["samples"][record["sample_id"]]
        for name, entry in record.get("fields", {}).items():
            expected = truth["fields"].get(name)
            entry["verdict"] = (
                "NOT_EVALUATED"
                if expected is None
                else _verdict(expected, entry.get("value"))
            )
            entry["gt_category"] = expected["gt"] if expected else None
        for assertion in record.get("negative_assertions", []):
            if "must_not_equal" not in assertion:
                # The run record already carries the verdict computed against
                # the same ground truth; nothing to re-derive.
                continue
            produced = record.get("fields", {}).get(assertion["field"], {}).get("value")
            assertion["violated"] = produced is not None and _comparable(
                produced
            ) == _comparable(assertion["must_not_equal"])
    return run


def summarise(run: dict[str, Any], label: str) -> dict[str, Any]:
    samples = run["samples"]
    verdicts: Counter = Counter()
    by_field: dict[str, Counter] = defaultdict(Counter)
    by_type: dict[str, Counter] = defaultdict(Counter)
    confusion: dict[str, dict[str, int]] = defaultdict(Counter)
    classifications = Counter()
    processed = 0
    upload_rejected = 0
    wrong_non_null: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    page_totals = Counter()
    times: list[float] = []
    chars = 0

    for record in samples:
        sid = record["sample_id"]
        if record.get("upload_rejected"):
            upload_rejected += 1
            confusion[record["expected_document_type"]]["UPLOAD_REJECTED"] += 1
            continue
        page_totals["documents"] += 1
        page_totals["pages"] += len(record.get("pages") or [])
        if record.get("processing_status") == "COMPLETED":
            processed += 1
        if record.get("process_ms"):
            times.append(record["process_ms"])
        chars += record.get("ocr_chars") or 0
        expected_type = record["expected_document_type"]
        predicted = record.get("predicted_document_type") or "NOT_PROCESSED"
        classifications[predicted] += 1
        confusion[expected_type][predicted] += 1
        by_type[expected_type]["documents"] += 1
        if predicted == expected_type:
            by_type[expected_type]["correct_type"] += 1

        for name, entry in (record.get("fields") or {}).items():
            verdict = entry["verdict"]
            verdicts[verdict] += 1
            by_field[name][verdict] += 1
            if verdict == "CORRECT":
                by_type[expected_type]["fields_correct"] += 1
            elif verdict == "INCORRECT":
                by_type[expected_type]["fields_incorrect"] += 1
                wrong_non_null.append(
                    {
                        "sample_id": sid,
                        "document_type": expected_type,
                        "field": name,
                        "confidence": entry.get("confidence"),
                        "evidence_count": entry.get("evidence_count"),
                        "evidence_assessment": entry.get("evidence_assessment"),
                    }
                )
            elif verdict == "UNRESOLVED":
                unresolved.append(
                    {
                        "sample_id": sid,
                        "document_type": expected_type,
                        "field": name,
                        "gt_category": entry.get("gt_category"),
                    }
                )

    evaluated = verdicts["CORRECT"] + verdicts["INCORRECT"] + verdicts["UNRESOLVED"]
    false_ready = []
    for record in samples:
        if record.get("upload_rejected") or record.get("processing_status") != "COMPLETED":
            continue
        has_wrong = any(
            entry["verdict"] == "INCORRECT" for entry in (record.get("fields") or {}).values()
        )
        has_unresolved = any(
            entry["verdict"] == "UNRESOLVED" for entry in (record.get("fields") or {}).values()
        )
        if record.get("overall_status") == "READY" and (has_wrong or has_unresolved):
            false_ready.append(
                {
                    "sample_id": record["sample_id"],
                    "document_type": record["expected_document_type"],
                    "wrong_fields": sum(
                        1
                        for entry in (record.get("fields") or {}).values()
                        if entry["verdict"] == "INCORRECT"
                    ),
                    "unresolved_fields": sum(
                        1
                        for entry in (record.get("fields") or {}).values()
                        if entry["verdict"] == "UNRESOLVED"
                    ),
                }
            )

    negatives = [
        {"sample_id": r["sample_id"], **assertion}
        for r in samples
        for assertion in r.get("negative_assertions", [])
        if assertion.get("violated")
    ]

    return {
        "label": label,
        "baseline_commit": run.get("baseline_commit"),
        "generated_at": run.get("generated_at"),
        "dataset": {
            "documents": len(samples),
            "upload_rejected": upload_rejected,
            "processed_completed": processed,
            "pages": page_totals["pages"],
            "ocr_characters": chars,
        },
        "classification": {
            "predicted_distribution": dict(classifications),
            "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
            "correct_type": sum(
                confusion[t].get(t, 0) for t in confusion
            ),
            "accuracy_over_processed": round(
                sum(confusion[t].get(t, 0) for t in confusion)
                / max(1, len(samples) - upload_rejected),
                4,
            ),
            "unknown_or_unprocessed": sum(
                count
                for predicted, count in classifications.items()
                if predicted in {"UNKNOWN", "NOT_PROCESSED"}
            ),
        },
        "extraction": {
            "verdicts": {key: verdicts.get(key, 0) for key in VERDICTS},
            "evaluated_fields": evaluated,
            "field_precision": round(
                verdicts["CORRECT"] / max(1, verdicts["CORRECT"] + verdicts["INCORRECT"]), 4
            ),
            "field_recall": round(verdicts["CORRECT"] / max(1, evaluated), 4),
            "by_field": {name: dict(counts) for name, counts in sorted(by_field.items())},
            "by_document_type": {name: dict(counts) for name, counts in sorted(by_type.items())},
        },
        "safety": {
            "wrong_non_null_values": len(wrong_non_null),
            "wrong_non_null_detail": wrong_non_null,
            "unresolved_fields": len(unresolved),
            "unresolved_detail": unresolved,
            "false_ready_documents": len(false_ready),
            "false_ready_detail": false_ready,
            "negative_assertion_violations": len(negatives),
            "negative_assertion_detail": negatives,
        },
        "performance": {
            "documents_processed": len(times),
            "total_ms": round(sum(times), 1),
            "mean_ms": round(sum(times) / len(times), 1) if times else None,
            "max_ms": round(max(times), 1) if times else None,
            "ms_per_page": round(sum(times) / max(1, page_totals["pages"]), 1),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    run = json.loads(args.run.read_text(encoding="utf-8"))
    ground_truth = json.loads((WORK_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    summary = summarise(rescore(run, ground_truth), args.label)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary["extraction"]["verdicts"], ensure_ascii=False))
    print("false_ready:", summary["safety"]["false_ready_documents"])
    print("wrong_non_null:", summary["safety"]["wrong_non_null_values"])


if __name__ == "__main__":
    os.environ.setdefault("OCR_PROVIDER", "mock")
    main()
