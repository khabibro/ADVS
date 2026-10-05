"""B0 vs B1 comparison from two score_v2 outputs (development or hold-out)."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metrics(d):
    a = d["aggregate"]
    pv = a["per_version"]
    out = {}
    for v in ("digital", "scanned", "images"):
        c = pv.get(v, {})
        out[v] = dict(correct=c.get("CORRECT", 0), wrong=c.get("WRONG", 0), unresolved=c.get("UNRESOLVED", 0), n=c.get("evaluated", 0),
                      acts=c.get("acts", 0), auto=c.get("auto_accepted", 0), false_auto=c.get("false_auto_accept", 0), ocr_n=c.get("ocr_evaluated", 0))
    out["burden"] = a["burden_needs_human_mean"]
    out["burden_total"] = a["burden_needs_human_total"]
    out["auto_decided"] = a["auto_decided"]
    out["false_ready"] = a["false_ready"]
    out["ready_on_record"] = a["ready_on_record"]
    out["status"] = a["status_comparison"]
    out["trusted_wrong"] = a["trusted_wrong_fields"]
    return out


def table(title, b0, b1):
    m0, m1 = metrics(load(b0)), metrics(load(b1))
    L = [f"### {title}\n", "| Metric | B0 | B1 |", "|---|---|---|"]
    for v in ("digital", "scanned", "images"):
        a, b = m0[v], m1[v]
        L.append(f"| {v}: CORRECT / WRONG / UNRESOLVED (of {a['n']}) | {a['correct']} / {a['wrong']} / {a['unresolved']} | {b['correct']} / {b['wrong']} / {b['unresolved']} |")
    for v in ("scanned", "images"):
        a, b = m0[v], m1[v]
        L.append(f"| {v}: OCR fields auto-accepted | {a['auto']} / {a['ocr_n']} ({100*a['auto']/max(1,a['ocr_n']):.1f}%) | {b['auto']} / {b['ocr_n']} ({100*b['auto']/max(1,b['ocr_n']):.1f}%) |")
        L.append(f"| {v}: false auto-accept | {a['false_auto']} | {b['false_auto']} |")
    for v in ("digital", "scanned", "images"):
        x, y = m0["burden"].get(v), m1["burden"].get(v)
        red = f" ({100*(x-y)/x:.0f}% lower)" if x and v != "digital" else ""
        L.append(f"| {v}: review burden (fields a human must confirm/supply per submission) | {x} | {y}{red} |")
    for v in ("scanned", "images"):
        a, b = m0["auto_decided"].get(v, {}), m1["auto_decided"].get(v, {})
        L.append(f"| {v}: auto-decided submissions (READY/NEEDS_CORRECTION with no human step) | {a.get('auto_decided', 0)}/{a.get('submissions', 0)} | {b.get('auto_decided', 0)}/{b.get('submissions', 0)} |")
    L.append(f"| False READY | {len(m0['false_ready'])} {m0['false_ready']} | {len(m1['false_ready'])} {m1['false_ready']} |")
    L.append(f"| Effective (acted-on) wrong fields | {m0['trusted_wrong']} | {m1['trusted_wrong']} |")
    L.append(f"| READY on RECORD rows | {m0['ready_on_record']} | {m1['ready_on_record']} |")
    L.append(f"| Status vs expectation | {m0['status']} | {m1['status']} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    print(table(sys.argv[3] if len(sys.argv) > 3 else "B0 vs B1", sys.argv[1], sys.argv[2]))
