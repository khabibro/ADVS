"""Scoreboard for the automation loop (private inputs, masked output).

    python3 loop_score.py --private data/private_real --arm results/loop/c0 --biz results/loop/c0/biz [--tag c0]

Per family (student: fresh/seed A/seed B; business) and medium: valid submissions, READY, correct READY (READY and no
wrong effective value), wrong READY, negatives READY, auto-accepted fields (correct/wrong), mean blockers per valid
submission. Only counts are printed; individual failures are not (validation sets are read in aggregate only).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_categories import analyse, load_runs  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--private", default="data/private_real")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--biz", required=True)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()
    res = analyse(load_runs(args))
    subs, items = res["subs"], res["items"]
    rows = defaultdict(Counter)
    base = {"business": Path(args.biz)}
    for fam in ("fresh", "seedA", "seedB"):
        base[fam] = Path(args.arm) / fam
    for s in subs:
        path = Path(args.private) / base[s["family"]] / f"sub_{s['sub']}.json"
        try:
            s["issues"] = len(json.loads(path.read_text(encoding="utf-8"))["verification"]["issues"])
        except (OSError, KeyError, ValueError):
            s["issues"] = len(s["blockers"])
        for key in (s["family"], "student" if s["family"] != "business" else "business", "ALL"):
            r = rows[key]
            if s["kind"] == "valid":
                r["valid"] += 1
                r["ready"] += s["status"] == "READY"
                r["valid_needs_correction"] += s["status"] == "NEEDS_CORRECTION"
                r["correct_ready"] += s["status"] == "READY" and not s["wrong_effective"]
                r["wrong_ready"] += s["status"] == "READY" and s["wrong_effective"]
                r["blockers"] += s["issues"]
            else:
                r["negatives"] += 1
                r["negatives_ready"] += s["status"] == "READY"
    for it in items:
        for key in (it["family"], "student" if it["family"] != "business" else "business", "ALL"):
            rows[key]["fields"] += 1
            rows[key]["auto_correct"] += it["outcome"] == "CORRECT_ACCEPTED"
            rows[key]["auto_wrong"] += it["outcome"] == "WRONG_ACCEPTED"
    out = {}
    for key, r in rows.items():
        out[key] = dict(r) | {"mean_blockers": round(r["blockers"] / r["valid"], 2) if r["valid"] else None}
        v = out[key]
        print(f"{key:9s} valid {v.get('valid',0):3d} READY {v.get('ready',0):3d} correctREADY {v.get('correct_ready',0):3d} wrongREADY {v.get('wrong_ready',0)} validNEEDS_CORRECTION {v.get('valid_needs_correction',0)}"
              f" | negatives {v.get('negatives',0):3d} READY {v.get('negatives_ready',0)} | verification issues per valid submission {v['mean_blockers']}")
    if args.out_json:
        Path(args.out_json).write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
