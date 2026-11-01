"""Fictional documents vs real documents: where does the gap come from? (private inputs, masked output)

    python3 fictional_vs_real.py --private data/private_real --arm results/final2/off \
        --fict-v3 results/final2/off/dev.v3.json --fict-cache evaluation/phase_d/ocr_cache --out-json out.json

Two stages per field of a real document with a confirmed gold value:
  OCR stage         the gold value can be read in the OCR text of the page (compared in memory, never printed)
  extraction stage  of the fields whose value IS in the text: the machine value equals the gold value
and the decision the system took (auto-accepted / sent to a person). Fictional documents have no gold text, so
their OCR+extraction result is one number per type (v3 scorer); the digital (text layer) versions give the
extraction stage alone, the scanned/photo versions the two stages together.
Effective text height: median OCR line height in pixels (the cache or run records the line boxes).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_categories import field_outcome, load_runs, present_in_text  # noqa: E402
from score_variants_real import wilson  # noqa: E402


def ci(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% ({100 * lo:.1f}-{100 * hi:.1f})"


def line_heights(pages: list[dict]) -> list[float]:
    heights = []
    for page in pages:
        for line in page.get("lines", []):
            box = line.get("bounding_box") or {}
            if box.get("width") and box.get("height"):
                heights.append(min(box["width"], box["height"]) if box["width"] < box["height"] else box["height"])
    return heights


def real_stages(args) -> dict:
    subs = load_runs(argparse.Namespace(private=args.private, arm=args.arm, biz=args.biz))
    table: dict = defaultdict(lambda: defaultdict(int))
    heights: dict = defaultdict(list)
    for sub in subs:
        if sub["kind"] != "valid":
            continue
        family = "business" if sub["family"] == "business" else "student"
        for doc in sub["docs"]:
            for name, (expected, f, norm) in doc["fields"].items():
                key = (family, doc["doctype"], name, doc["medium"])
                t = table[key]
                t["n"] += 1
                in_text = present_in_text(name, expected, doc["text"]) if doc["text"] else doc["medium"] == "digital"
                t["ocr_ok"] += in_text
                outcome = field_outcome(norm, name, expected, f)
                correct = outcome in ("CORRECT_ACCEPTED", "CORRECT_REVIEW")
                t["extract_ok_given_text"] += in_text and correct
                t["in_text"] += in_text
                t["correct"] += correct
                t["accepted_correct"] += outcome == "CORRECT_ACCEPTED"
                t["wrong_accepted"] += outcome == "WRONG_ACCEPTED"
    return {"table": {"|".join(k): dict(v) for k, v in table.items()}, "heights": {}}


def fict_stage(v3_paths: list[Path]) -> dict:
    out: dict = defaultdict(lambda: defaultdict(int))
    for path in v3_paths:
        agg = json.loads(path.read_text(encoding="utf-8"))["aggregate"]
        for key, v in agg["fields"].items():
            doctype, version = key.split("|")
            t = out[(doctype, version)]
            t["evaluated"] += v.get("evaluated", 0)
            t["correct"] += v.get("CORRECT", 0) + v.get("NE_CORRECT_ABSTENTION", 0)
        for version, v in agg["per_version"].items():
            out[("ALL", version)]["auto_accepted"] += v.get("auto_accepted", 0)
            out[("ALL", version)]["evaluated"] += v.get("evaluated", 0)
    return {"|".join(k): dict(v) for k, v in out.items()}


def fict_heights(cache_dirs: list[Path], manifest_paths: list[Path]) -> dict:
    """Median OCR line height of the scanned/photo fictional documents (from the recorded OCR cache)."""
    import hashlib

    by_style: dict = defaultdict(list)
    for cache, manifest in zip(cache_dirs, manifest_paths):
        files = json.loads(manifest.read_text(encoding="utf-8"))["files"]
        for entry in files:
            if entry.get("style") == "digital":
                continue
            sha = entry["sha256"]
            cached = cache / f"{sha}.json"
            if not cached.exists():
                continue
            pages = json.loads(cached.read_text(encoding="utf-8")).get("pages", [])
            by_style[entry.get("style", "?")].extend(line_heights(pages))
    return {k: {"median": statistics.median(v), "n": len(v)} for k, v in by_style.items() if v}


def real_heights(run_dirs: list[Path]) -> dict:
    by: dict = defaultdict(list)
    for d in run_dirs:
        for f in d.glob("sub_*_ocr.json"):
            for _name, pages in json.loads(f.read_text(encoding="utf-8")).items():
                if any(p["metadata"].get("source") != "ocr" for p in pages):
                    continue
                by[d.name].extend(line_heights(pages))
    return {k: {"median": statistics.median(v), "n": len(v)} for k, v in by.items() if v}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--private", default="data/private_real")
    ap.add_argument("--arm", default="results/final2/off")
    ap.add_argument("--biz", default="results/biz_frozen")
    ap.add_argument("--fict-v3", nargs="*", default=[])
    ap.add_argument("--fict-cache", nargs="*", default=[])
    ap.add_argument("--fict-manifest", nargs="*", default=[])
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()
    out = {"real": real_stages(args)}
    out["fictional"] = fict_stage([Path(p) for p in args.fict_v3])
    out["fict_heights"] = fict_heights([Path(p) for p in args.fict_cache], [Path(p) for p in args.fict_manifest])
    arm = Path(args.private) / args.arm
    out["real_heights"] = real_heights([arm / s for s in ("fresh", "seedA", "seedB")])
    text = json.dumps(out, ensure_ascii=False, indent=1)
    if args.out_json:
        Path(args.out_json).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
