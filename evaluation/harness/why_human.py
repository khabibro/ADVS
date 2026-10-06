"""Why is a human still needed? Breakdown of the OCR fields (scanned + images) of a scored v2 run
that have no effective value, by reason code. Reads the output of score_v2 / score_d2."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def reasons(path: str) -> Counter:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    raw, scored = d["raw"]["sets"], d["scored"]["sets"]
    counts: Counter = Counter()
    for sid, sset in scored.items():
        for version in ("scanned", "images"):
            vres = sset["versions"].get(version)
            if not vres:
                continue
            raw_files = {f["file"]: f for f in raw[sid]["versions"][version]["files"]}
            for f in vres["files"]:
                for name, fs in f["fields"].items():
                    if fs["category"] not in ("EVALUATED", "NOT_EVALUATED") or fs["acts"]:
                        continue
                    info = raw_files[f["file"]]["fields"].get(name, {})
                    meta = raw_files[f["file"]].get("classification_meta") or {}
                    auto = info.get("auto_acceptance") or {}
                    if fs["category"] == "NOT_EVALUATED":
                        reason = "ABSENT_IN_DOCUMENT"
                    elif meta.get("needs_review"):
                        reason = "UNCERTAIN_TYPE:" + str((meta.get("title_gate") or {}).get("reason") or "classification")
                    elif info.get("machine_value") is None:
                        reason = "NOT_EXTRACTED"
                    elif auto.get("reason"):
                        reason = auto["reason"]
                    else:
                        reason = "NO_DECISION_RECORD"
                    counts[(reason, name)] += 1
    return counts


def render(paths: dict[str, str]) -> str:
    out = ["# Why a human is still needed (scanned + images; fields with no effective value)\n"]
    for label, path in paths.items():
        c = reasons(path)
        total = sum(c.values())
        out.append(f"## {label}: {total} fields\n")
        by_reason = Counter()
        for (reason, _), n in c.items():
            by_reason[reason] += n
        out.append("| Reason | Fields | Share | Fields affected (count) |")
        out.append("|---|---|---|---|")
        for reason, n in by_reason.most_common():
            names = Counter({name: m for (r, name), m in c.items() if r == reason})
            out.append(f"| {reason} | {n} | {100 * n / max(1, total):.0f}% | " + ", ".join(f"{k} {v}" for k, v in names.most_common(6)) + " |")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    pairs = dict(item.split("=", 1) for item in sys.argv[2:])
    Path(sys.argv[1]).write_text(render(pairs), encoding="utf-8")
    print(render(pairs))
