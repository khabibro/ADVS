"""Variant harness CLI (raw capture; scoring lives in score_v2.py / score_variants.py).

Runs a corpus through the real production service path; see harness_core.py.

Usage (from apps/api):
    .venv312/bin/python ../../evaluation/harness/run_variants.py \
        --corpus dev --output ../../evaluation/phase_d/B0_raw.json \
        [--sets B01,B02] [--versions digital,scanned,images] [--skip-ocr] [--skip-formats] \
        [--project-values] [--ocr-cache DIR --ocr-mode record|replay] [--strategy S0..S5]

`--corpus holdout` is refused unless ADVS_FINAL_JUDGEMENT=1 (final judgement only).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_core import Runner, guard_corpus  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", choices=["dev", "holdout"], default="dev")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sets", type=str, default=None)
    parser.add_argument("--versions", type=str, default="digital,scanned,images")
    parser.add_argument("--skip-ocr", action="store_true", help="digital only")
    parser.add_argument("--skip-formats", action="store_true")
    parser.add_argument("--project-values", action="store_true")
    parser.add_argument("--ocr-cache", type=Path, default=None)
    parser.add_argument("--ocr-mode", choices=["live", "record", "replay"], default="live")
    parser.add_argument("--strategy", default=None, help="auto-acceptance strategy S0..S5")
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    guard_corpus(args.corpus)  # refuses the hold-out set without the env switch (and logs it)
    versions = [v.strip() for v in args.versions.split(",") if v.strip()]
    if args.skip_ocr:
        versions = [v for v in versions if v == "digital"]
    wanted = {s.strip() for s in args.sets.split(",")} if args.sets else None
    extra_env = {"ADVS_AUTO_ACCEPT_STRATEGY": args.strategy} if args.strategy else {}

    runner = Runner(
        args.corpus,
        ocr_mode=args.ocr_mode,
        ocr_cache_dir=args.ocr_cache,
        project_values=args.project_values,
        extra_env=extra_env,
    )
    try:
        results = runner.run_corpus(versions, wanted, include_formats=not args.skip_formats)
    finally:
        runner.close()
    results["strategy"] = args.strategy
    results["label"] = args.label
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
