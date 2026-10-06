"""Learn from human review decisions (Phase D3, D3-10). Offline, report only.

Reads stored field reviews (CONFIRMED / CORRECTED, with the machine value, the reviewed value and the
OCR confidence) and writes, per field type:
  * the observed error rate (corrections / decided reviews),
  * a confidence-vs-error table,
  * the OCR confusions seen in corrections (read character -> true character), as *candidates* for
    the confusion table.
It never changes the policy: updating thresholds or the confusion table stays a reviewed code change.

Usage:  python calibrate_from_reviews.py --database-url sqlite:///x.db --out report.md
Library: analyse(records) -> dict;  render(analysis) -> markdown.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BINS = [(0.0, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 0.98), (0.98, 0.995), (0.995, 1.01)]


def confusions(original: str, reviewed: str) -> list[tuple[str, str]]:
    """Character substitutions between two strings of the same length (one pair per differing
    position). A length change (a dropped or added character) is reported separately."""
    if len(original) != len(reviewed):
        return []
    return [(a, b) for a, b in zip(original, reviewed, strict=True) if a != b]


def analyse(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_field: dict[str, dict[str, Any]] = defaultdict(lambda: {"confirmed": 0, "corrected": 0, "bins": defaultdict(lambda: [0, 0]), "confusions": Counter(), "length_changes": 0})
    for record in records:
        decision = record["decision"]
        if decision not in ("CONFIRMED", "CORRECTED"):
            continue
        entry = by_field[record["field_name"]]
        wrong = decision == "CORRECTED"
        entry["corrected" if wrong else "confirmed"] += 1
        confidence = record.get("confidence")
        if confidence is not None:
            for index, (low, high) in enumerate(BINS):
                if low <= confidence < high:
                    entry["bins"][index][0] += int(wrong)
                    entry["bins"][index][1] += 1
        if wrong:
            original, reviewed = record.get("original") or "", record.get("reviewed") or ""
            pairs = confusions(original, reviewed)
            if pairs:
                entry["confusions"].update(pairs)
            elif original != reviewed:
                entry["length_changes"] += 1
    return {name: {**value, "bins": {k: tuple(v) for k, v in value["bins"].items()}} for name, value in by_field.items()}


def render(analysis: dict[str, Any]) -> str:
    lines = ["# Review-decision calibration (report only; no policy is changed)\n"]
    if not analysis:
        lines.append("No review decisions available.")
        return "\n".join(lines) + "\n"
    lines.append("| Field | Decided | Corrected | Error rate | " + " | ".join(f"[{lo:.3f},{min(hi, 1):.3f})" for lo, hi in BINS) + " |")
    lines.append("|---|---|---|---|" + "---|" * len(BINS))
    for name, item in sorted(analysis.items()):
        total = item["confirmed"] + item["corrected"]
        cells = [f"{item['bins'].get(i, (0, 0))[0]} / {item['bins'].get(i, (0, 0))[1]}" for i in range(len(BINS))]
        lines.append(f"| {name} | {total} | {item['corrected']} | {item['corrected'] / total:.3f} | " + " | ".join(cells) + " |")
    lines.append("\n## Confusions seen in corrections (candidates for the confusion table)\n")
    lines.append("| Field | read → true | count |")
    lines.append("|---|---|---|")
    for name, item in sorted(analysis.items()):
        for (read, true), count in item["confusions"].most_common(10):
            lines.append(f"| {name} | {read} → {true} | {count} |")
        if item["length_changes"]:
            lines.append(f"| {name} | (dropped / added character) | {item['length_changes']} |")
    return "\n".join(lines) + "\n"


def load_records(database_url: str) -> list[dict[str, Any]]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.models.entities import ExtractedField, FieldReview

    engine = create_engine(database_url)
    out = []
    with Session(engine) as db:
        for review in db.scalars(select(FieldReview)).all():
            field = db.get(ExtractedField, review.extracted_field_id) if review.extracted_field_id else None
            out.append(
                {
                    "field_name": review.field_name,
                    "decision": review.decision,
                    "original": review.original_normalized_value,
                    "reviewed": review.reviewed_normalized_value,
                    "confidence": field.confidence if field else None,
                }
            )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    text = render(analyse(load_records(args.database_url)))
    args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
