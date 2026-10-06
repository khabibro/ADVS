"""Strategy comparison table: every strategy x every metric, for the development set and the
injection suite. Reads evaluation/phase_d/strategies/*.json (score_v2 output and inject_errors output)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "evaluation" / "phase_d" / "strategies"
STRATS = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def inj_totals(inj: dict) -> dict:
    single_fa = single_fr = corr_fa = corr_fr = both_fa = both_fr = 0
    exercised = effective = 0
    corr_cases = 0
    for key, t in inj["summary"].items():
        exercised += t["cases"]
        effective += t["effective"]
        scope = key.split("-")[1] if "-" in key else "one"
        both = key.endswith("-both")
        if both:
            both_fa += t["false_auto_accept"]
            both_fr += t["false_ready"]
        elif scope == "all":
            corr_fa += t["false_auto_accept"]
            corr_fr += t["false_ready"]
            corr_cases += t["cases"]
        else:
            single_fa += t["false_auto_accept"]
            single_fr += t["false_ready"]
    return dict(single_fa=single_fa, single_fr=single_fr, corr_fa=corr_fa, corr_fr=corr_fr, both_fa=both_fa, both_fr=both_fr, exercised=exercised, effective=effective)


def main() -> None:
    for mode in ("noproj", "proj"):
        print(f"\n### Project values: {'yes' if mode == 'proj' else 'no'}\n")
        print("| Strategy | OCR auto-accept rate (scanned / images) | false auto-accept (dev) | false READY (dev) | needs-human fields per submission (scanned / images) | auto-decided submissions (scanned / images) | digital CORRECT / WRONG | injection: single-doc false accept / READY | correlated (E2,E3,E5,E7 all): false accept / READY | both-passes: false accept / READY |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for s in STRATS:
            d = load(ROOT / f"{s}_{mode}.json")
            inj = load(ROOT / f"inj_{s}_{mode}.json")
            if not d:
                continue
            a = d["aggregate"]
            pv = a["per_version"]
            def rate(v):
                c = pv.get(v, {})
                return f"{100*c.get('auto_accepted',0)/max(1,c.get('ocr_evaluated',1)):.1f}%"
            fa = sum(pv.get(v, {}).get("false_auto_accept", 0) for v in ("scanned", "images"))
            ad = a["auto_decided"]
            dg = pv.get("digital", {})
            ij = inj_totals(inj) if inj else None
            print(
                f"| {s} | {rate('scanned')} / {rate('images')} | {fa} | {len(a['false_ready'])} | "
                f"{a['burden_needs_human_mean'].get('scanned')} / {a['burden_needs_human_mean'].get('images')} | "
                f"{ad.get('scanned', {}).get('auto_decided', 0)}/{ad.get('scanned', {}).get('submissions', 0)} / {ad.get('images', {}).get('auto_decided', 0)}/{ad.get('images', {}).get('submissions', 0)} | "
                f"{dg.get('CORRECT', 0)} / {dg.get('WRONG', 0)} | "
                + (f"{ij['single_fa']} / {ij['single_fr']} | {ij['corr_fa']} / {ij['corr_fr']} | {ij['both_fa']} / {ij['both_fr']} |" if ij else "- | - | - |")
            )


if __name__ == "__main__":
    main()
