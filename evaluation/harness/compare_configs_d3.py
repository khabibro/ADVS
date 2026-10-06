"""Step-4 configuration comparison for Phase D3 -> evaluation/phase_d3/D3_configs.md.

Reads the scored runs (`<LABEL>_<corpus>.json`) and injection summaries (`<LABEL>_inj_<corpus>.json`)
for each configuration and prints, per configuration: false READY, false auto-accept (single-error
injections, correlated/both-pass reported separately where the suite names them), decision-blocking
burden (headline) next to total unconfirmed fields, auto-decided submissions, and mean processing time.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "phase_d3"
CORPORA = ("dev", "holdout", "holdout2")


def load(label: str, corpus: str) -> dict:
    return json.loads((D / f"{label}_{corpus}.json").read_text(encoding="utf-8"))


def injections(label: str, corpus: str) -> dict[str, dict]:
    return json.loads((D / f"{label}_inj_{corpus}.json").read_text(encoding="utf-8"))["summary"]


def blocking(d: dict, version: str) -> float:
    values = [
        len(v.get("review_items", []))
        for s in d["raw"]["sets"].values()
        for ver, v in s["versions"].items()
        if ver == version
    ]
    return round(statistics.mean(values), 2)


def main(configs: dict[str, str]) -> str:
    out = ["# Phase D3 configuration comparison (development data: test_variants, hold-out 1, hold-out 2)\n"]
    out.append(
        "| Config | Corpus | false READY | decision-blocking scanned / images | total unconfirmed scanned / images "
        "| auto-decided scanned / images | mean process ms |"
    )
    out.append("|---|---|---|---|---|---|---|")
    for label, desc in configs.items():
        for corpus in CORPORA:
            d = load(label, corpus)
            agg = d["aggregate"]
            ad = agg["auto_decided"]
            out.append(
                f"| {label} ({desc}) | {corpus} | {len(agg['false_ready'])} "
                f"| {blocking(d, 'scanned')} / {blocking(d, 'images')} "
                f"| {agg['burden_needs_human_mean']['scanned']} / {agg['burden_needs_human_mean']['images']} "
                f"| {ad['scanned']['auto_decided']}/{ad['scanned']['submissions']} / "
                f"{ad['images']['auto_decided']}/{ad['images']['submissions']} "
                f"| {agg['process_ms_mean']['scanned']} / {agg['process_ms_mean']['images']} |"
            )
    out.append("\n## Injections E1-E18: false auto-accept / false READY (classes with a non-zero count are listed)\n")
    out.append("| Config | Corpus | cases | false auto-accept | false READY | classes with a non-zero count |")
    out.append("|---|---|---|---|---|---|")
    for label in configs:
        for corpus in CORPORA:
            summary = injections(label, corpus)
            cases = sum(v["cases"] for v in summary.values())
            fa = sum(v["false_auto_accept"] for v in summary.values())
            fr = sum(v["false_ready"] for v in summary.values())
            bad = ", ".join(
                f"{k} ({v['false_auto_accept']}/{v['false_ready']})"
                for k, v in summary.items()
                if v["false_auto_accept"] or v["false_ready"]
            )
            out.append(f"| {label} | {corpus} | {cases} | {fa} | {fr} | {bad or '-'} |")
    return "\n".join(out)


if __name__ == "__main__":
    print(main(dict(item.split("=", 1) for item in sys.argv[1:])))
