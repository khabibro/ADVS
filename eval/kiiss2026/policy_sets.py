"""Named policy lists for run_corpus.py (evaluation only)."""

from __future__ import annotations

import json
from pathlib import Path

from policies import Policy

COARSE_TAU = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.975, 0.98, 0.985,
              0.99, 0.992, 0.994, 0.996, 0.998, 0.999, 1.0001]
DENSE_TAU = sorted({round(0.50 + 0.01 * i, 3) for i in range(41)} | {round(0.90 + 0.001 * i, 3) for i in range(100)} | {1.0001})
KINDS = {"CONF": "conf", "CONFG": "conf_gated", "CONFF": "conf_fmt"}


def tau_name(prefix: str, tau: float) -> str:
    return f"{prefix}@{tau:g}"


def baselines(grid: list[float]) -> list[Policy]:
    return [Policy(tau_name(prefix, t), kind, t) for prefix, kind in KINDS.items() for t in grid]


def advs_family() -> list[Policy]:
    return [
        Policy("ADVS"),
        Policy("ABL-a_no_docs", off_docs=True),
        Policy("ABL-b_no_app", off_app=True),
        Policy("ABL-c_no_second", off_second=True),
        Policy("ABL-d_no_internal", off_internal=True),
        Policy("H14", h14=True),
        Policy("NONE", "none"),
    ]


def _selected(tau_file: Path | None) -> list[Policy]:
    if tau_file is None:
        return []
    chosen = json.loads(Path(tau_file).read_text(encoding="utf-8"))
    return [Policy(f"{prefix}*@{chosen[prefix]['tau']:g}", kind, chosen[prefix]["tau"]) for prefix, kind in KINDS.items()]


def main_set(tau_file: Path | None) -> list[Policy]:
    return advs_family() + baselines(COARSE_TAU) + _selected(tau_file)


def select_set(tau_file: Path | None) -> list[Policy]:
    return [Policy("ADVS")] + baselines(DENSE_TAU)


def p1_set(tau_file: Path | None) -> list[Policy]:
    return advs_family()


POLICY_SETS = {"main": main_set, "select": select_set, "p1": p1_set}
