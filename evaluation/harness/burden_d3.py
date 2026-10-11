"""Decision-blocking burden (headline metric from Phase D3) next to the total unconfirmed fields.

decision-blocking = review-queue items of the submission: fields that a configured rule or a default
required field uses and that are not yet confirmed (services/reviews.review_items).
total unconfirmed = score_v2's `needs_human` count (every manifest field without an effective value).
Reads a score_v2/score_d2 output (its `raw` carries `review_items`)."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def burden(path: str) -> dict[str, dict[str, float]]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out: dict[str, dict[str, float]] = {}
    blocking: dict[str, list[int]] = {}
    for sid, sset in d["raw"]["sets"].items():
        for version, vres in sset["versions"].items():
            if version == "digital_partial_checklist":
                continue
            blocking.setdefault(version, []).append(len(vres.get("review_items", [])))
    for version, values in blocking.items():
        out[version] = {
            "blocking_mean": round(statistics.mean(values), 2),
            "unconfirmed_mean": d["aggregate"]["burden_needs_human_mean"].get(version),
            "submissions": len(values),
        }
    return out


def render(runs: dict[str, str]) -> str:
    lines = ["| Run | Version | decision-blocking / submission | total unconfirmed / submission |", "|---|---|---|---|"]
    for label, path in runs.items():
        for version, v in burden(path).items():
            lines.append(f"| {label} | {version} | {v['blocking_mean']} | {v['unconfirmed_mean']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(dict(item.split("=", 1) for item in sys.argv[1:])))
