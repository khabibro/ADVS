"""Phase G merge-gate numbers from the scored runs written by dev_gates.sh / the final judgement.

  python evaluation/phase_g/scripts/gate_summary.py <results-dir> <label> corpus [corpus ...]
(corpus names as in the file names: dev, holdout, holdout2, holdout3)
"""
import json
import math
import sys
from pathlib import Path


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def main() -> None:
    out_dir, label, *corpora = sys.argv[1:]
    out_dir = Path(out_dir)
    print(f"# Gate summary {label}\n")
    print("| corpus | files scored | false READY (submissions) | digital field accuracy | scan field accuracy | photo field accuracy | university_name scan / photo | review fields per submission scan / photo | auto-decided scan / photo |")
    print("|---|---|---|---|---|---|---|---|---|")
    inj_rows = []
    for c in corpora:
        scored = json.loads((out_dir / f"{label}_{c}.json").read_text(encoding="utf-8"))
        agg = scored["aggregate"]
        pv = agg["per_version"]
        fr = agg.get("false_ready", [])
        tally = {"digital": [0, 0], "scanned": [0, 0], "images": [0, 0]}
        uni = {"scanned": [0, 0], "images": [0, 0]}
        for block in (scored["scored"]["sets"],):
            for entry in block.values():
                for ver, v in entry["versions"].items():
                    base = "digital" if ver.startswith("digital") else ver
                    for f in v.get("files", []):
                        for name, fs in (f.get("fields") or {}).items():
                            if fs.get("category") != "EVALUATED" or base not in tally:
                                continue
                            tally[base][1] += 1
                            tally[base][0] += fs["outcome"] == "CORRECT"
                            if name == "university_name" and base in uni:
                                uni[base][1] += 1
                                uni[base][0] += fs["outcome"] == "CORRECT"
        def pct(t):
            return f"{t[0]}/{t[1]}" + (f" ({100 * t[0] / t[1]:.1f}%)" if t[1] else "")
        burden = agg.get("burden_needs_human_mean", {})
        auto = {k: f"{v['auto_decided']}/{v['submissions']}" for k, v in agg.get("auto_decided", {}).items()}
        print(f"| {c} | {len(scored['scored']['sets'])} sets | {len(fr)} | {pct(tally['digital'])} | {pct(tally['scanned'])} | {pct(tally['images'])} | {pct(uni['scanned'])} / {pct(uni['images'])} | {burden.get('scanned')} / {burden.get('images')} | {auto.get('scanned')} / {auto.get('images')} |")
        p = out_dir / f"{label}_inj_{c}.json"
        if p.exists():
            inj_rows.append((c, json.loads(p.read_text(encoding="utf-8"))["results"]))
    print("\n## Injected-error suites E1-E18\n")
    print("| corpus | cases | false auto-accept (single-error classes) | false auto-accept (E3c-both, owner-accepted residual) | false READY (other cases) | false READY (that residual case) | 95% upper bound for false READY (rule of three) |")
    print("|---|---|---|---|---|---|---|")
    for c, results in inj_rows:
        ex = [r for r in results if r.get("exercised", True)]
        def residual(r):  # the owner-accepted H14 case: both OCR passes make the same error (E3c, both passes)
            return "H14/" in r["case"] and r["error"].startswith("E3c") and bool(r.get("both_passes"))

        fa_single = [r for r in ex if r["false_auto_accept"] and not residual(r)]
        fa_both = [r for r in ex if r["false_auto_accept"] and residual(r)]
        fr = [r for r in ex if r["false_ready"] and not residual(r)]
        fr_res = [r for r in ex if r["false_ready"] and residual(r)]
        n = len(ex)
        print(f"| {c} | {n} | {len(fa_single)} | {len(fa_both)} | {len(fr)} | {len(fr_res)} | {3 / n:.2%} |")
        for r in fa_single + fr:
            print(f"|  leak: {r['case']} | | | | | |")


main()
