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

#: Fields a reviewer can settle with one click (crop + value, Enter): issue dates, GPA whose arithmetic is not
#: evaluable, and the dates that are otherwise decision-robust.
ONE_CLICK_FIELDS = frozenset({"issue_date", "gpa", "valid_until", "valid_from"})


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
            s["verification_issues"] = json.loads(path.read_text(encoding="utf-8"))["verification"]["issues"]
            s["issues"] = len(s["verification_issues"])
        except (OSError, KeyError, ValueError):
            s["verification_issues"] = []
            s["issues"] = len(s["blockers"])
        for key in dict.fromkeys((s["family"], "student" if s["family"] != "business" else "business", "ALL")):
            r = rows[key]
            if s["kind"] == "valid":
                r["valid"] += 1
                r["ready"] += s["status"] == "READY"
                r["valid_needs_correction"] += s["status"] == "NEEDS_CORRECTION"
                r["correct_ready"] += s["status"] == "READY" and not s["wrong_effective"]
                r["wrong_ready"] += s["status"] == "READY" and s["wrong_effective"]
                r["blockers"] += s["issues"]
                # READY after at most N staff confirmations: every verification issue is a field issue on a
                # one-click field, and no wrong value was auto-accepted in the submission (a reviewer corrects
                # the blocking fields). Document-level issues (missing, expired, unclassified) are not one-click.
                found = s.get("verification_issues", [])
                fields = {(i["document_type"], i["field_name"]) for i in found if i.get("field_name")}
                ready_ok = s["status"] == "READY" and not s["wrong_effective"]
                one_click = (
                    s["status"] != "READY"
                    and not s["wrong_effective"]
                    and bool(found)
                    and all(i.get("field_name") in ONE_CLICK_FIELDS for i in found)
                )
                r["after_0"] += ready_ok
                for limit in (1, 2, 3):
                    r[f"after_le{limit}"] += ready_ok or (one_click and len(fields) <= limit)
                r["after_any_one_click"] += ready_ok or one_click
            else:
                r["negatives"] += 1
                r["negatives_ready"] += s["status"] == "READY"
    for it in items:
        for key in dict.fromkeys((it["family"], "student" if it["family"] != "business" else "business", "ALL")):
            rows[key]["fields"] += 1
            rows[key]["auto_correct"] += it["outcome"] == "CORRECT_ACCEPTED"
            rows[key]["auto_wrong"] += it["outcome"] == "WRONG_ACCEPTED"
    out = {}
    for key, r in rows.items():
        out[key] = dict(r) | {"mean_blockers": round(r["blockers"] / r["valid"], 2) if r["valid"] else None}
        v = out[key]
        print(f"{key:9s} valid {v.get('valid',0):3d} READY {v.get('ready',0):3d} correctREADY {v.get('correct_ready',0):3d} wrongREADY {v.get('wrong_ready',0)} validNEEDS_CORRECTION {v.get('valid_needs_correction',0)}"
              f" | negatives {v.get('negatives',0):3d} READY {v.get('negatives_ready',0)} | verification issues per valid submission {v['mean_blockers']}")
        print(f"          READY after at most N staff confirmations (valid, 0 wrong auto-accepted): 0:{v.get('after_0',0)}  <=1:{v.get('after_le1',0)}  <=2:{v.get('after_le2',0)}  <=3:{v.get('after_le3',0)}  any one-click set:{v.get('after_any_one_click',0)}  of {v.get('valid',0)}")
    if args.out_json:
        Path(args.out_json).write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
