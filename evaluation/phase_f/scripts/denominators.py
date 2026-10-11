"""Phase F: denominators and uncertainty for the safety claims, from committed scored runs only.

Reads evaluation/phase_d2/{B2_D2_dev,B2_D2_holdout,H2_B1}.json (scored runs on development data,
hold-out 1 and hold-out 2). Never touches hold-out set 3. Writes nothing but stdout.

  python3 evaluation/phase_f/scripts/denominators.py > evaluation/phase_f/results/denominators.txt
"""

import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNS = {
    "dev (test_variants), final policy B2-D2": "evaluation/phase_d2/B2_D2_dev.json",
    "hold-out 1 (development data since D2), final policy B2-D2": "evaluation/phase_d2/B2_D2_holdout.json",
    "hold-out 2 (judged once, before the final policy), B1-D2": "evaluation/phase_d2/H2_B1.json",
}
RUNS_PHASE_G = {  # `--phase-g`: the same counts for the final code (development corpora) and for hold-out 3 (judged once)
    "dev (test_variants), Phase G final code": "evaluation/phase_g/results/dev_final/F_dev.json",
    "hold-out 1 (development data), Phase G final code": "evaluation/phase_g/results/dev_final/F_holdout.json",
    "hold-out 2 (development data), Phase G final code": "evaluation/phase_g/results/dev_final/F_holdout2.json",
    "hold-out 3 (judged once), main baseline": "evaluation/phase_g/final/H3_main.json",
    "hold-out 3 (judged once), Phase G integrated": "evaluation/phase_g/final/H3_integrated.json",
}
VERSIONS = ("digital", "scanned", "images")


def upper_bound_95(n: int) -> float:
    """Rule of three: with 0 events in n trials the 95 % upper bound is about 3/n."""
    return 3 / n if n else float("nan")


def main() -> None:
    per_field = {v: collections.defaultdict(collections.Counter) for v in VERSIONS}
    totals = {v: collections.Counter() for v in VERSIONS}
    fields = {v: collections.Counter() for v in VERSIONS}
    unresolved = collections.Counter()
    runs = RUNS_PHASE_G if "--phase-g" in sys.argv else RUNS
    for name, rel in runs.items():
        data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        print(f"\n## {name}  ({rel})")
        for version in VERSIONS:
            c = collections.Counter()
            for set_id, s in data["scored"]["sets"].items():
                v = s["versions"].get(version)
                if not v:
                    continue
                expected = re.sub(r"^\(digital expectation\)\s*", "", v["expected_status"])
                actual = v["actual_status"]
                c["submissions"] += 1
                if v.get("false_ready"):
                    c["false_ready"] += 1
                if "record actual" in expected or " or " in expected:
                    c["correct_status_undefined"] += 1
                elif expected == "READY":
                    c["correct_READY"] += 1
                    c["READY_expected_not_READY"] += actual != "READY"
                else:
                    c["correct_not_READY"] += 1
                c["actual_REVIEW_REQUIRED"] += actual == "REVIEW_REQUIRED"
                c["needs_human>0"] += v["burden"]["needs_human"] > 0
                for f in v["files"]:
                    for field, fv in f.get("fields", {}).items():
                        if fv.get("category") != "EVALUATED":
                            continue
                        if "hold-out 3" in name:  # judged once: reported on its own, never pooled with development data
                            continue
                        fields[version][fv["outcome"]] += 1
                        per_field[version][field][fv["outcome"]] += 1
                        if version != "digital" and fv["outcome"] != "CORRECT":
                            unresolved[(f["expected"], field)] += 1
            print(f"  {version:8} " + ", ".join(f"{k}={c[k]}" for k in sorted(c)))
            if "hold-out 3" not in name:
                totals[version].update(c)
            elif "--phase-g" in sys.argv:
                n3 = c["correct_not_READY"]
                print(f"           -> not-READY submissions n={n3}, false READY={c['false_ready']}, 95% upper bound (rule of three) = {upper_bound_95(n3):.1%}")
    print("\n## Totals over the three corpora (the same 22-25 scenarios, different values: NOT independent samples)")
    for version in VERSIONS:
        t = totals[version]
        n = t["correct_not_READY"]
        print(f"  {version:8} submissions whose correct status is not READY: n={n}; false READY observed={t['false_ready']}; "
              f"95% upper bound on the false-READY rate (rule of three) = {upper_bound_95(n):.1%}")
    print("\n## Injected-error suites (cases are derived from the same base documents: bounds are optimistic)")
    suites = (("E1-E18 Phase G final code, development", 1354), ("E1-E18 Phase G final code, hold-out 1", 1532),
              ("E1-E18 Phase G final code, hold-out 2", 1523), ("E1-E18 Phase G final code, hold-out 3 (judged once)", 1525)) if "--phase-g" in sys.argv else (("E1-E12, development", 474), ("E1-E12, hold-out 1", 666),
                     ("E1-E18 baseline B0_D3 (main policy), development", 1353),
                     ("E1-E18 baseline B0_D3, hold-out 1", 1532), ("E1-E18 baseline B0_D3, hold-out 2", 1523))
    for label, n in suites:
        print(f"  {label:55} n={n:5}  upper bound for 0 events = {upper_bound_95(n):.2%}")
    print("\n## Machine values (OCR/embedded text) before any acceptance policy, evaluated fields")
    for version in VERSIONS:
        f = fields[version]
        n = sum(f.values())
        print(f"  {version:8} n={n}: " + ", ".join(f"{k}={v}" for k, v in sorted(f.items()))
              + f"  -> wrong={f['WRONG']} ({f['WRONG']/n:.1%}), unresolved={f['UNRESOLVED']} ({f['UNRESOLVED']/n:.1%})")
    print("\n## Exact-match per field (machine value, all three corpora): CORRECT / evaluated")
    names = sorted({f for v in VERSIONS for f in per_field[v]})
    print(f"  {'field':32}" + "".join(f"{v:>16}" for v in VERSIONS))
    for field in names:
        row = ""
        for v in VERSIONS:
            c = per_field[v].get(field)
            row += f"{(str(c['CORRECT']) + ' / ' + str(sum(c.values()))) if c else '-':>16}"
        print(f"  {field:32}{row}")
    print("\n## Fields that were not CORRECT on scans/photos (all three corpora)")
    by_field = collections.Counter()
    for (doc, field), count in unresolved.items():
        by_field[(doc, field)] += count
    total = sum(by_field.values())
    for (doc, field), count in by_field.most_common():
        print(f"  {count:3}  {doc}.{field}")
    print(f"  total {total}")


if __name__ == "__main__":
    main()
