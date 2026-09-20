"""Generates a human-readable Markdown report from one or two evaluation
result JSON files (dev and/or held_out). Dev and held-out numbers are never
merged into a single headline figure -- see evaluation/README.md policy.

Usage:
    cd apps/api && .venv/bin/python scripts/eval_report.py \\
        --dev evaluation/results/mock_dev.json \\
        --held-out evaluation/results/mock_held_out.json \\
        --output evaluation/reports/baseline_2026-09-09.md
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_lib import paths


def _confusion_table(matrix: dict) -> str:
    types = list(matrix.keys())
    header = "| Gold \\ Pred | " + " | ".join(types) + " |"
    sep = "|---" * (len(types) + 1) + "|"
    rows = [header, sep]
    for gold in types:
        row = [str(matrix[gold].get(pred, 0)) for pred in types]
        rows.append(f"| {gold} | " + " | ".join(row) + " |")
    return "\n".join(rows)


def _section(title: str, payload: dict) -> str:
    repro = payload["reproducibility"]
    c, e, v, fc = (
        payload["classification"],
        payload["extraction"],
        payload["validation"],
        payload["failure_categories"],
    )

    lines = [f"## {title}", ""]
    lines.append(
        f"Samples: {repro['sample_count']} | split: {repro['split']} | mode: {repro['mode']} | "
        f"classifier: {repro['classifier_version']} | extractor: {repro['extractor_version']} | "
        f"validation engine: {repro['validation_engine_version']} | git: {repro['git_commit']} | "
        f"evaluated_at: {repro['evaluated_at']}"
    )
    lines.append("")
    lines.append("### Classification")
    lines.append(
        f"- Total: {c['total']}, correct: {c['correct']}, incorrect: {c['incorrect']}, "
        f"predicted UNKNOWN: {c['unknown_predicted']}"
    )
    lines.append(
        f"- **Accuracy: {c['accuracy']:.2%}** (heuristic score, not a calibrated probability)"
    )
    lines.append(f"- Review rate: {c['review_rate']:.2%}")
    ca = c["confidence_analysis"]
    lines.append(
        f"- Mean score when correct: {ca['correct_score_mean']}, when incorrect: {ca['incorrect_score_mean']}"
    )
    lines.append("")
    lines.append("Per-class accuracy:")
    for k, v2 in c["per_class_accuracy"].items():
        lines.append(f"- {k}: {v2['correct']}/{v2['total']} ({v2['accuracy']:.2%})")
    lines.append("")
    lines.append("Confusion matrix:")
    lines.append("")
    lines.append(_confusion_table(c["confusion_matrix"]))
    lines.append("")

    lines.append("### Extraction")
    lines.append(
        f"- Field total: {e['field_total']}, correct: {e['field_correct']}, "
        f"missing: {e['field_missing']}, false value: {e['field_false_value']}"
    )
    lines.append(f"- **Field accuracy: {e['field_accuracy']:.2%}**")
    lines.append(f"- Missing-value rate: {e['missing_value_rate']:.2%}")
    lines.append(
        f"- **False-value rate: {e['false_value_rate']:.2%}** (a value was invented/wrong, not just absent)"
    )
    lines.append(
        f"- **Document-level required-field success: {e['document_level_success_rate']:.2%}** "
        f"({e['document_level_success_count']}/{e['document_level_total']}) -- ALL required fields correct"
    )
    lines.append("")
    lines.append("Per-field:")
    for name, stats in e["per_field"].items():
        lines.append(
            f"- {name}: {stats['correct']}/{stats['total']} correct, {stats['missing']} missing, "
            f"{stats['false_value']} false"
        )
    lines.append("")

    lines.append("### Validation")
    if v["total"]:
        lines.append(f"- Total scored: {v['total']}, correct: {v['correct']} ({v['accuracy']:.2%})")
        lines.append(f"- **False READY: {v['false_ready_count']}** {v['false_ready_samples']}")
        lines.append(
            f"- False NEEDS_CORRECTION: {v['false_needs_correction_count']} {v['false_needs_correction_samples']}"
        )
        lines.append("")
        lines.append("Confusion matrix:")
        lines.append("")
        lines.append(_confusion_table(v["confusion_matrix"]))
    else:
        lines.append("- No samples had a scorable gold validation status in this split.")
    lines.append("")

    lines.append("### Error categories")
    lines.append(f"- Total failing samples: {fc['total_failing_samples']}")
    for cat, stats in fc["by_category"].items():
        lines.append(f"- {cat}: {stats['count']} ({stats['pct']:.1%})")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Markdown evaluation report.")
    parser.add_argument("--dev", type=Path, default=None)
    parser.add_argument("--held-out", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", default="ADVS P1.5 Evaluation")
    args = parser.parse_args()

    parts = [f"# {args.title}", ""]
    if args.dev:
        parts.append(
            _section(
                "Development set (dev, ~70% of synthetic samples)",
                json.loads(args.dev.read_text(encoding="utf-8")),
            )
        )
    if args.held_out:
        parts.append(
            _section(
                "Held-out set (held_out, ~30% -- NOT used to tune any heuristic)",
                json.loads(args.held_out.read_text(encoding="utf-8")),
            )
        )
    parts.append(
        "## Scope note\n\n"
        "All numbers above are from the **synthetic** benchmark "
        "(`evaluation/datasets/synthetic/`). No real or anonymized documents "
        "have been evaluated -- see `evaluation/datasets/real/README.md`. "
        "Do not read these numbers as real-world accuracy."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(parts), encoding="utf-8")
    resolved = args.output.resolve()
    try:
        shown = resolved.relative_to(paths.REPO_ROOT)
    except ValueError:
        shown = resolved
    print(f"Report written to {shown}")


if __name__ == "__main__":
    main()
