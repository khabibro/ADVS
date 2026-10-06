"""Confidence-vs-error calibration table from a scored v2 run (development set, OCR documents only)."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

BINS = [(0.0, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 0.98), (0.98, 0.995), (0.995, 1.01)]


def main(scored_json: str, out_md: str) -> None:
    data = json.loads(Path(scored_json).read_text(encoding="utf-8"))
    raw = data["raw"]["sets"]
    scored = data["scored"]["sets"]
    rows: dict[str, list[tuple[float, bool]]] = defaultdict(list)
    for sid, sset in scored.items():
        for version in ("scanned", "images"):
            vres = sset["versions"].get(version)
            if not vres:
                continue
            raw_files = {f["file"]: f for f in raw[sid]["versions"][version]["files"]}
            for f in vres["files"]:
                for name, fs in f["fields"].items():
                    if fs["category"] != "EVALUATED" or fs["actual"] is None:
                        continue
                    conf = raw_files[f["file"]]["fields"].get(name, {}).get("confidence")
                    if conf is None:
                        continue
                    rows[name].append((conf, fs["outcome"] == "CORRECT"))
    lines = ["# Calibration: OCR confidence vs correctness (development set, scanned + images)\n",
             "Only values the extractor produced are counted. A bin shows `wrong / total`.\n",
             "| Field | n | wrong | highest-confidence wrong | " + " | ".join(f"[{lo:.3f},{min(hi,1):.3f})" for lo, hi in BINS) + " |",
             "|---|---|---|---|" + "---|" * len(BINS)]
    for name, items in sorted(rows.items()):
        wrong = [c for c, ok in items if not ok]
        cells = []
        for lo, hi in BINS:
            inbin = [(c, ok) for c, ok in items if lo <= c < hi]
            cells.append(f"{sum(1 for _, ok in inbin if not ok)} / {len(inbin)}")
        lines.append(f"| {name} | {len(items)} | {len(wrong)} | {max(wrong):.3f} |" if wrong else f"| {name} | {len(items)} | 0 | - |")
        lines[-1] += " " + " | ".join(cells) + " |"
    Path(out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
