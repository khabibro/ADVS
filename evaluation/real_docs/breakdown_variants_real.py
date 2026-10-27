"""Break down every scored field of a variant run (private input, masked output; no values printed).

    python3 breakdown_variants_real.py --run RESULTS --submissions SUBMISSIONS.json --gold gold.json --out OUT.csv

Categories per scored field (gold has a value, or is absent):
  CORRECT_ACCEPTED   machine value right and accepted without a person
  CORRECT_REVIEW     machine value right, a person still confirms it (reason = the policy reason)
  MISSING            no machine value (a person supplies it; reason: unclassified document / not found)
  WRONG_CAUGHT       machine value wrong, NOT accepted (a person sees it and corrects it)
  WRONG_ACCEPTED     machine value wrong AND accepted (the failure the project must never have)
  ABSENT_OK          field absent in the document, none produced
Negative cases whose image was deliberately edited score the edited value as WRONG by design; they are reported
separately as EDITED_*.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_real import norm  # noqa: E402

TYPE_BY_KEY = {"재학증명서": "ENROLLMENT_CERTIFICATE", "성적증명서": "TRANSCRIPT"}
EDITED = {"n_date_edited": {"issue_date"}, "n_gpa_edited": {"gpa"}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--submissions", type=Path, required=True)
    ap.add_argument("--gold", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    gold = {g["document_type"]: g for g in json.loads(a.gold.read_text(encoding="utf-8"))["documents"].values()}
    rows = []
    for sub in json.loads(a.submissions.read_text(encoding="utf-8")):
        p = a.run / f"sub_{sub['id']}.json"
        if not p.exists():
            continue
        run = json.loads(p.read_text(encoding="utf-8"))
        for rec in run["documents"]:
            key = next((k for k in TYPE_BY_KEY if k in rec["file"]), None)
            if key is None or "combined" in rec["file"] or (sub["id"] == "n_identity_mismatch" and key == "성적증명서"):
                continue
            dtype = TYPE_BY_KEY[key]
            classified = rec.get("predicted_document_type") == dtype
            for name, spec in gold[dtype]["fields"].items():
                f = (rec.get("fields") or {}).get(name) or {}
                machine, effective = f.get("machine_value"), f.get("value")
                ar = f.get("auto_acceptance") or {}
                reason = ar.get("reason") or f.get("evidence_state") or ""
                if spec["state"] == "VERIFIED_ABSENT":
                    cat = "ABSENT_OK" if machine is None else ("WRONG_ACCEPTED" if effective is not None else "WRONG_CAUGHT")
                    reason = ""
                else:
                    exp = norm(name, spec["value"])
                    if machine is None:
                        cat, reason = "MISSING", ("document not classified" if not classified else "label or value not read")
                    elif norm(name, machine) == exp:
                        cat = "CORRECT_ACCEPTED" if effective is not None else "CORRECT_REVIEW"
                        if cat == "CORRECT_ACCEPTED":
                            reason = ""
                    else:
                        cat = "WRONG_ACCEPTED" if effective is not None else "WRONG_CAUGHT"
                        if name in EDITED.get(sub["id"], set()):
                            cat = "EDITED_" + cat
                rows.append({"submission": sub["id"], "group": sub["group"], "document": dtype, "field": name, "category": cat, "reason": reason})
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    cats = ["CORRECT_ACCEPTED", "CORRECT_REVIEW", "MISSING", "WRONG_CAUGHT", "WRONG_ACCEPTED", "EDITED_WRONG_CAUGHT", "ABSENT_OK"]
    print("\nBY GROUP (fields):")
    print(f"{'group':14s}" + "".join(f"{c[:14]:>15s}" for c in cats) + f"{'total':>7s}")
    by_group = defaultdict(Counter)
    by_field = defaultdict(Counter)
    for r in rows:
        by_group[r["group"]][r["category"]] += 1
        by_field[(r["document"][:5], r["field"])][r["category"]] += 1
    for g, c in list(by_group.items()) + [("ALL", sum((c for c in by_group.values()), Counter()))]:
        print(f"{g:14s}" + "".join(f"{c.get(k, 0):>15d}" for k in cats) + f"{sum(c.values()):>7d}")
    print("\nBY FIELD:")
    for k, c in sorted(by_field.items()):
        print(f"{k[0]:6s}{k[1]:16s}" + "".join(f"{c.get(x, 0):>15d}" for x in cats))
    print("\nREVIEW REASONS (correct values still sent to a person):")
    for reason, n in Counter(r["reason"] for r in rows if r["category"] == "CORRECT_REVIEW").most_common():
        print(f"  {n:4d}  {reason}")
    print("\nMISSING by cause:")
    for reason, n in Counter((r["reason"], r["field"]) for r in rows if r["category"] == "MISSING").most_common():
        print(f"  {n:4d}  {reason}")
    print("\nWRONG_CAUGHT reasons:", Counter(r["reason"] for r in rows if r["category"].endswith("WRONG_CAUGHT")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
