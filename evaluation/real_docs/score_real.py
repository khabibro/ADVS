"""Score a run_real.py output against the owner-confirmed gold (private). Prints masked results only.

    python3 evaluation/real_docs/score_real.py --run data/private_real/results/baseline --gold data/private_real/gold.json
"""
from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path


def norm(field: str, v):
    if v is None:
        return None
    s = "".join(unicodedata.normalize("NFKC", str(v)).split())
    if field == "student_id":
        s = "".join(c for c in s if c.isdigit())
    if field == "gpa":
        s = f"{float(s):.2f}"
    if field == "gpa_scale":
        s = f"{float(s):g}"
    return s


def mask(field: str, v) -> str:
    if v is None:
        return "-"
    s = str(v)
    if field in ("student_name",):
        return s[0] + "*" * (len(s) - 2) + s[-1] if len(s) > 2 else s
    if field == "student_id":
        return s[:2] + "*" * (len(s) - 4) + s[-2:]
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--gold", type=Path, required=True)
    ap.add_argument("--tag", default="submission_all")
    a = ap.parse_args()
    gold = json.loads(a.gold.read_text(encoding="utf-8"))["documents"]
    run = json.loads((a.run / f"{a.tag}.json").read_text(encoding="utf-8"))
    rows = []
    for rec in run["documents"]:
        g = gold.get(rec["file"])
        if g is None:
            continue
        fields = rec.get("fields") or {}
        rows.append({"file": "doc:" + g["document_type"], "field": "document_type", "gold": g["document_type"],
                     "machine": rec.get("predicted_document_type"), "outcome": "CORRECT" if rec.get("predicted_document_type") == g["document_type"] else "WRONG",
                     "decision": "needs_review" if (rec.get("classification_meta") or {}).get("needs_review") else "ok", "reason": ""})
        for name, spec in g["fields"].items():
            f = fields.get(name) or {}
            machine, effective = f.get("machine_value"), f.get("value")
            if spec["state"] == "VERIFIED_ABSENT":
                outcome = "CORRECT_ABSTENTION" if machine is None else "WRONG"
                exp = None
            else:
                exp = norm(name, spec["value"])
                outcome = "MISSING" if machine is None else ("CORRECT" if norm(name, machine) == exp else "WRONG")
            decision = "AUTO_ACCEPTED" if effective is not None else "REVIEW"
            ar = f.get("auto_acceptance") or {}
            reason = ar.get("reason") or f.get("evidence_state") or ""
            rows.append({"file": g["document_type"], "field": name, "gold": mask(name, spec.get("value")), "machine": mask(name, machine),
                         "outcome": outcome, "decision": decision, "reason": f"{f.get('extraction_method') or ''} {reason}".strip()})
    n = len(rows)
    scored = [r for r in rows if r["field"] != "document_type"]
    summ = {"documents_typed_correctly": sum(r["outcome"] == "CORRECT" for r in rows if r["field"] == "document_type"),
            "documents": sum(r["field"] == "document_type" for r in rows),
            "fields": len(scored), "correct": sum(r["outcome"] in ("CORRECT", "CORRECT_ABSTENTION") for r in scored),
            "wrong": sum(r["outcome"] == "WRONG" for r in scored), "missing": sum(r["outcome"] == "MISSING" for r in scored),
            "auto_accepted": sum(r["decision"] == "AUTO_ACCEPTED" for r in scored),
            "wrong_auto_accepted": sum(r["decision"] == "AUTO_ACCEPTED" and r["outcome"] == "WRONG" for r in scored),
            "review_fields_gold_present": sum(r["decision"] == "REVIEW" and r["outcome"] != "CORRECT_ABSTENTION" for r in scored),
            "submission_status": run["verification"].get("status")}
    (a.run / "SCORE.json").write_text(json.dumps({"summary": summ, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows:
        print(f"{r['file']:22s} {r['field']:16s} gold={r['gold']:18s} machine={r['machine'] or '-':18s} {r['outcome']:18s} {r['decision']:13s} {r['reason'][:60]}")
    print(summ)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
