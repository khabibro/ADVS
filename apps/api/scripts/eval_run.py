"""Runs the P1.5 evaluation pipeline against the synthetic (or real, once
labeled) benchmark.

Usage:
    cd apps/api && .venv/bin/python scripts/eval_run.py --mode mock --split dev
    cd apps/api && .venv/bin/python scripts/eval_run.py --mode mock --split held_out
    cd apps/api && .venv/bin/python scripts/eval_run.py --mode paddle   # real OCR
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_lib import paths
from eval_lib.runner import RunConfig, run_mock, run_paddle


def _write_csv(payload: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sample_id",
                "source_type",
                "document_type_gold",
                "document_type_pred",
                "classification_correct",
                "review",
                "required_fields_correct",
                "required_fields_total",
                "validation_gold",
                "validation_pred",
                "failure_category",
                "processing_ms",
            ]
        )
        for s in payload.get("samples", []):
            writer.writerow(
                [
                    s["sample_id"],
                    s["source"],
                    s["document_type_gold"],
                    s["document_type_pred"],
                    s["classification_correct"],
                    s["classification_needs_review"],
                    s["required_fields_correct"],
                    s["required_fields_total"],
                    s["validation_gold"] or "",
                    s["validation_pred"] or "",
                    s["failure_category"] or "",
                    s["processing_ms"],
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the P1.5 evaluation pipeline.")
    parser.add_argument("--mode", choices=["mock", "paddle"], default="mock")
    parser.add_argument("--split", choices=["dev", "held_out"], default=None)
    parser.add_argument("--output", default=None, help="Result file basename (without extension)")
    parser.add_argument(
        "--source-class",
        choices=["OFFICIAL_PUBLIC_REFERENCE", "RECREATED_FROM_PUBLIC_REFERENCE", "SYNTHETIC_REALISTIC", "NEGATIVE_OUT_OF_SCOPE"],
        default=None,
        help="Score only samples of this source_class (see evaluation/README.md)",
    )
    args = parser.parse_args()

    output_name = args.output or f"{args.mode}_{args.split or 'all'}"
    config = RunConfig(mode=args.mode, split=args.split, output_name=output_name, source_class=args.source_class)

    payload = run_mock(config) if args.mode == "mock" else run_paddle(config)

    paths.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = paths.RESULTS_DIR / f"{output_name}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Results written to {json_path.relative_to(paths.REPO_ROOT)}")

    if "samples" in payload:
        csv_path = paths.RESULTS_DIR / f"{output_name}.csv"
        _write_csv(payload, csv_path)
        print(f"CSV written to {csv_path.relative_to(paths.REPO_ROOT)}")

        c, e, v = payload["classification"], payload["extraction"], payload["validation"]
        print(f"Classification accuracy: {c['accuracy']:.2%} ({c['correct']}/{c['total']})")
        print(f"Extraction field accuracy: {e['field_accuracy']:.2%} ({e['field_correct']}/{e['field_total']})")
        print(f"Document-level extraction success: {e['document_level_success_rate']:.2%}")
        if v["total"]:
            print(f"Validation accuracy: {v['accuracy']:.2%} ({v['correct']}/{v['total']})")
            print(f"False READY count: {v['false_ready_count']}")


if __name__ == "__main__":
    main()
