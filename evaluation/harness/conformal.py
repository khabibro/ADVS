"""Split-conformal calibration of auto-acceptance confidence thresholds (Phase D3, D3-11).

Framework only: nothing in production uses it yet. Given labelled field outcomes (confidence,
correct) from a calibration split and a target false-accept rate alpha, it returns, per field type,
the lowest confidence threshold tau such that the finite-sample bound

        (wrong_accepted(tau) + 1) / (accepted(tau) + 1)  <=  alpha

holds (conformal risk control with a 0/1 loss). With no wrong value among n accepted the bound is
1/(n+1), so alpha is only reachable with at least ceil(1/alpha) - 1 accepted examples: the report
states that sample size, and says "insufficient data" instead of guessing when it is not met.

The bound is marginal over exchangeable data. The development data are synthetic, so the thresholds
it suggests are for comparison only until real reviewed data exist.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def required_samples(alpha: float) -> int:
    return max(1, math.ceil(1 / alpha) - 1)


def threshold(outcomes: list[tuple[float, bool]], alpha: float) -> dict[str, Any]:
    """outcomes: (confidence, correct). Returns {"threshold", "accepted", "wrong", "bound"} or
    {"threshold": None, "reason": ...}."""
    need = required_samples(alpha)
    ordered = sorted(outcomes, key=lambda item: item[0])
    best: dict[str, Any] | None = None
    # candidate thresholds: each distinct confidence; accepted = all examples with conf >= tau
    for index, (tau, _) in enumerate(ordered):
        if index and ordered[index - 1][0] == tau:
            continue
        accepted = ordered[index:]
        wrong = sum(1 for _, ok in accepted if not ok)
        bound = (wrong + 1) / (len(accepted) + 1)
        if bound <= alpha and len(accepted) >= need:
            best = {"threshold": tau, "accepted": len(accepted), "wrong": wrong, "bound": round(bound, 4)}
            break  # the lowest feasible threshold accepts the most
    if best is not None:
        return best
    return {"threshold": None, "reason": "insufficient data" if len(ordered) < need else "no threshold meets alpha", "needed": need, "have": len(ordered)}


def suggest(records: list[dict[str, Any]], alpha: float) -> dict[str, dict[str, Any]]:
    """records: {"field_name", "confidence", "correct"}; one threshold per field name."""
    grouped: dict[str, list[tuple[float, bool]]] = defaultdict(list)
    for record in records:
        if record.get("confidence") is not None:
            grouped[record["field_name"]].append((float(record["confidence"]), bool(record["correct"])))
    return {name: threshold(items, alpha) for name, items in sorted(grouped.items())}


def render(suggestions: dict[str, dict[str, Any]], current: dict[str, float], alpha: float) -> str:
    lines = [f"# Conformal threshold suggestions (alpha = {alpha}; samples needed per field >= {required_samples(alpha)})\n", "Suggested only; production keeps the hand-picked floor.\n", "| Field | current floor | suggested threshold | accepted | wrong | bound |", "|---|---|---|---|---|---|"]
    for name, item in suggestions.items():
        floor = current.get(name, "-")
        if item["threshold"] is None:
            lines.append(f"| {name} | {floor} | — ({item['reason']}: have {item['have']}, need {item['needed']}) | | | |")
        else:
            lines.append(f"| {name} | {floor} | {item['threshold']:.3f} | {item['accepted']} | {item['wrong']} | {item['bound']} |")
    return "\n".join(lines) + "\n"
