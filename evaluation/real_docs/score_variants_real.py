"""Score a run_real.py --submissions output against the confirmed gold (private) and the variant expectations.

    python3 score_variants_real.py --run RESULTS_DIR --submissions variants/seedX/SUBMISSIONS.json --gold gold.json

Prints and writes (private) per-submission rows plus masked per-group totals with Wilson / rule-of-three bounds.
Field outcomes use the same definitions as score_real.py:
  CORRECT / WRONG / MISSING (machine value), CORRECT_ABSTENTION (field absent in gold and none produced),
  decision AUTO_ACCEPTED when an effective value exists, otherwise REVIEW.
False READY = status READY while any effective (auto-accepted or reviewed) value is wrong, or for a negative case whose
expected outcome is "never READY". Wrong auto-accepts = AUTO_ACCEPTED fields whose value differs from the gold.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_real import norm  # noqa: E402

TYPE_BY_KEY = {"재학증명서": "ENROLLMENT_CERTIFICATE", "성적증명서": "TRANSCRIPT"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - m) / d), min(1.0, (c + m) / d)


def fmt_ci(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    if k == 0:
        return f"0/{n} (rule of three upper {100 * 3 / n:.1f}%; Wilson {100 * wilson(k, n)[0]:.1f}-{100 * wilson(k, n)[1]:.1f}%)"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100 * k / n:.1f}%, Wilson {100 * lo:.1f}-{100 * hi:.1f}%)"


def doc_key(file: str) -> str | None:
    for key in TYPE_BY_KEY:
        if key in file:
            return key
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--submissions", type=Path, required=True)
    ap.add_argument("--gold", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    gold = json.loads(a.gold.read_text(encoding="utf-8"))["documents"]
    gold_by_type = {g["document_type"]: g for g in gold.values()}
    subs = json.loads(a.submissions.read_text(encoding="utf-8"))
    rows, groups = [], defaultdict(lambda: defaultdict(int))
    for sub in subs:
        path = a.run / f"sub_{sub['id']}.json"
        if not path.exists():
            continue
        run = json.loads(path.read_text(encoding="utf-8"))
        status = run["verification"].get("status")
        g = groups[sub["group"]]
        g["submissions"] += 1
        wrong_effective = 0
        for rec in run["documents"]:
            key = doc_key(rec["file"])
            fields = rec.get("fields") or {}
            if key is None or "combined" in rec["file"] or sub["id"] == "n_identity_mismatch" and key == "성적증명서":
                continue  # multi-page / fictional documents are judged by status only
            g["documents"] += 1
            expected_type = TYPE_BY_KEY[key]
            g["type_correct"] += rec.get("predicted_document_type") == expected_type
            gd = gold_by_type[expected_type]
            for name, spec in gd["fields"].items():
                f = fields.get(name) or {}
                machine, effective = f.get("machine_value"), f.get("value")
                if spec["state"] == "VERIFIED_ABSENT":
                    outcome = "CORRECT_ABSTENTION" if machine is None else "WRONG"
                else:
                    exp = norm(name, spec["value"])
                    outcome = "MISSING" if machine is None else ("CORRECT" if norm(name, machine) == exp else "WRONG")
                accepted = effective is not None
                if spec["state"] == "VERIFIED_ABSENT":
                    eff_wrong = accepted
                else:
                    eff_wrong = accepted and norm(name, effective) != norm(name, spec["value"])
                g["fields"] += 1
                g["correct"] += outcome in ("CORRECT", "CORRECT_ABSTENTION")
                g["wrong"] += outcome == "WRONG"
                g["missing"] += outcome == "MISSING"
                g["auto_accepted"] += accepted
                g["wrong_auto_accepted"] += eff_wrong
                g["review_fields"] += (not accepted) and outcome != "CORRECT_ABSTENTION"
                wrong_effective += eff_wrong
                rows.append({"sub": sub["id"], "group": sub["group"], "doc": expected_type, "field": name, "outcome": outcome, "accepted": accepted,
                             "wrong_effective": eff_wrong, "machine_len": len(str(machine)) if machine else 0})
        never_ready = sub["group"] == "negative" and "READY" not in sub["expected"].replace("NOT READY", "")
        false_ready = status == "READY" and (wrong_effective > 0 or never_ready)
        g["false_ready"] += false_ready
        g["ready"] += status == "READY"
        g["needs_correction"] += status == "NEEDS_CORRECTION"
        g["review_required"] += status == "REVIEW_REQUIRED"
        g["auto_decided"] += status in ("READY", "NEEDS_CORRECTION")
        rows.append({"sub": sub["id"], "group": sub["group"], "status": status, "expected": sub["expected"][:90], "false_ready": false_ready,
                     "issues": sorted({i.get("code") for i in run["verification"].get("issues", []) if i.get("code")})})
    total = defaultdict(int)
    for g in groups.values():
        for k, v in g.items():
            total[k] += v
    print(f"{'group':14s} {'subs':>4s} {'docs':>4s} {'type ok':>8s} {'fields ok':>10s} {'wrong':>5s} {'miss':>5s} {'auto':>5s} {'wrongAuto':>9s} {'review/sub':>10s} {'FalseREADY':>10s}")
    for name, g in list(groups.items()) + [("ALL", total)]:
        rps = g["review_fields"] / g["submissions"] if g["submissions"] else 0
        print(f"{name:14s} {g['submissions']:4d} {g['documents']:4d} {g['type_correct']:4d}/{g['documents']:<3d} {g['correct']:4d}/{g['fields']:<5d} {g['wrong']:5d} {g['missing']:5d} {g['auto_accepted']:5d} {g['wrong_auto_accepted']:9d} {rps:10.2f} {g['false_ready']:10d}")
    print("false READY:", fmt_ci(total["false_ready"], total["submissions"]))
    print("wrong auto-accepted fields:", fmt_ci(total["wrong_auto_accepted"], total["auto_accepted"] or total["fields"]))
    for r in rows:
        if "status" in r and (r.get("false_ready") or r["status"] == "READY"):
            print("  !!", r)
    out = a.out or a.run / "SCORE_VARIANTS.json"
    out.write_text(json.dumps({"groups": {k: dict(v) for k, v in groups.items()}, "total": dict(total), "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
