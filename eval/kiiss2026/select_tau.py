"""Choose the matched-review-burden thresholds on the DEVELOPMENT set only.

Input : runs/summary_dev_P0_select.json (run_corpus.py --corpus dev --policy-set select --kind clean)
Rule  : review burden = mean number of fields a person must still confirm or supply per submission,
        pooled over the scanned and photographed clean submissions of the development set.
        For each baseline family the tau on the dense dev grid whose burden is closest to the burden
        of ADVS (as reported, strategy S8) is chosen; ties go to the higher tau (the safer side).
Output: selected_tau.json (read by the main run). No hold-out data is read by this script.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def pooled_burden(rows: list[dict]) -> tuple[float, int, int]:
    ocr = [r for r in rows if r["version"] in ("scanned", "images")]
    fields = sum(r["review_fields"] for r in ocr)
    subs = sum(r["submissions"] for r in ocr)
    return fields / subs, fields, subs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    data = json.loads(a.summary.read_text(encoding="utf-8"))
    assert data["corpus"] == "dev" and data["pass"] == "P0"
    by_policy = {c["policy"]: c["rows"] for c in data["clean"]}
    target, target_fields, subs = pooled_burden(by_policy["ADVS"])
    chosen: dict = {"_rule": __doc__.strip().splitlines()[0], "_advs_dev_burden": target, "_advs_dev_review_fields": target_fields,
                    "_dev_ocr_submissions": subs}
    for prefix in ("CONF", "CONFG", "CONFF"):
        best = None
        curve = []
        for name, rows in by_policy.items():
            if not name.startswith(prefix + "@"):
                continue
            tau = float(name.split("@")[1])
            burden, fields, _ = pooled_burden(rows)
            curve.append((tau, burden))
            key = (abs(burden - target), -tau)
            if best is None or key < best[0]:
                best = (key, tau, burden, fields)
        _, tau, burden, fields = best
        chosen[prefix] = {"tau": tau, "dev_burden": burden, "dev_review_fields": fields, "abs_gap": abs(burden - target)}
        print(f"{prefix}: tau*={tau:g} dev burden {burden:.3f} (ADVS {target:.3f}) gap {abs(burden-target):.3f}")
    a.out.write_text(json.dumps(chosen, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
