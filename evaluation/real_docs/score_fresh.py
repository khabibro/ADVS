"""Score a run_real.py --submissions run of the fresh-capture set against the owner-confirmed gold (private inputs).

    python3 score_fresh.py --run RESULTS_DIR --dir data/private_real/fresh

Prints masked counts only (no document values). Writes SCORE_FRESH.json next to the run (private).
Field outcome, per scored field of a document read inside a pair submission:
  CORRECT_ACCEPTED   machine value equals gold and an effective (auto-accepted) value exists
  CORRECT_REVIEW     machine value equals gold but it was sent to a person (reason counted)
  MISSING            no machine value although the gold has one
  WRONG_CAUGHT       machine value differs from gold (or appears where the gold is absent) and was not auto-accepted
  WRONG_ACCEPTED     the effective value differs from gold: the failure that matters
  CORRECT_ABSENT     the gold says the field is not printed and none was produced
False READY: status READY while any effective value in the submission is wrong.
Document type: per file, from single-file submissions (one denominator per file). A rejected upload is reported separately.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_real import norm  # noqa: E402
from score_variants_real import fmt_ci  # noqa: E402


def outcome(name: str, spec: dict, f: dict) -> tuple[str, bool]:
    machine, effective = f.get("machine_value"), f.get("value")
    accepted = effective is not None
    if spec["state"] == "VERIFIED_ABSENT":
        if machine is None and effective is None:
            return "CORRECT_ABSENT", False
        return ("WRONG_ACCEPTED" if accepted else "WRONG_CAUGHT"), accepted
    exp = norm(name, spec["value"])
    if accepted and norm(name, effective) != exp:
        return "WRONG_ACCEPTED", True
    if machine is None:
        return "MISSING", False
    if norm(name, machine) != exp:
        return "WRONG_CAUGHT", False
    return ("CORRECT_ACCEPTED" if accepted else "CORRECT_REVIEW"), False


def reason(f: dict) -> str:
    ar = f.get("auto_acceptance") or {}
    return str(ar.get("reason") or f.get("evidence_state") or "unknown")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    gold = json.loads((a.dir / "gold.json").read_text(encoding="utf-8"))["documents"]
    subs = json.loads((a.dir / "SUBMISSIONS.json").read_text(encoding="utf-8"))
    G = defaultdict(Counter)
    reasons = defaultdict(Counter)
    errors, rows, gpa_rows, expiry = [], [], [], []
    seen = 0
    for sub in subs:
        path = a.run / f"sub_{sub['id']}.json"
        if not path.exists():
            continue
        seen += 1
        run = json.loads(path.read_text(encoding="utf-8"))
        status = run["verification"].get("status")
        g = G[sub["group"]]
        wrong_eff = 0
        for rec in run["documents"]:
            doc = {Path(k).name: v for k, v in sub["docs"].items()}.get(rec["file"])
            if rec["upload_status"] != 201:
                errors.append({"sub": sub["id"], "file_doc": doc, "kind": "upload_rejected", "http": rec["upload_status"],
                               "code": (json.loads(rec["upload_error"]).get("detail", {}).get("code") if rec.get("upload_error", "").startswith("{") else rec.get("upload_error", "")[:60])})
                g["upload_rejected_docs"] += 1
                continue
            if rec.get("processing_status") != "COMPLETED" and rec.get("processing_error_code"):
                errors.append({"sub": sub["id"], "file_doc": doc, "kind": "processing_error", "code": rec.get("processing_error_code")})
            if doc is None:
                continue
            gd = gold[doc]
            if sub["kind"] == "single":
                g["type_docs"] += 1
                g["type_correct"] += rec.get("predicted_document_type") == gd["document_type"]
            if sub["kind"] != "pair":
                continue
            fields = rec.get("fields") or {}
            g["pair_docs"] += 1
            g["pair_type_correct"] += rec.get("predicted_document_type") == gd["document_type"]
            for name, spec in gd["fields"].items():
                o, eff_wrong = outcome(name, spec, fields.get(name) or {})
                g["fields"] += 1
                g[o] += 1
                wrong_eff += eff_wrong
                if o == "CORRECT_REVIEW":
                    reasons[sub["group"]][reason(fields[name])] += 1
                if o in ("MISSING", "CORRECT_REVIEW", "WRONG_CAUGHT", "WRONG_ACCEPTED"):
                    g["review_fields"] += o != "WRONG_ACCEPTED"
                rows.append({"sub": sub["id"], "group": sub["group"], "doc": doc, "field": name, "outcome": o})
                if name in ("gpa", "gpa_scale") and sub["group"] in ("G0_real_photo", "G1_flat"):
                    gpa_rows.append({"sub": sub["id"], "doc": doc, "field": name, "outcome": o, "machine": (fields.get(name) or {}).get("machine_value"),
                                     "accepted": (fields.get(name) or {}).get("value") is not None, "doc_issues": rec.get("issues")})
        if sub["kind"] in ("pair", "multipage"):
            g["submissions"] += 1
            g["status_" + str(status)] += 1
            false_ready = status == "READY" and wrong_eff > 0
            g["false_ready"] += false_ready
            g["issues_" + "+".join(sorted({i.get("code") for i in run["verification"].get("issues", [])}))] += 1
        if sub.get("extra_eval_dates"):
            ex = run.get("extra_verifications") or {}
            expiry.append({"sub": sub["id"], "main": (status, sorted({i["code"] for i in run["verification"].get("issues", [])})),
                           **{d: (v.get("status"), sorted({i["code"] for i in v.get("issues", [])})) for d, v in ex.items()}})
    header = f"{'group':26s} {'subs':>4s} {'type(single)':>13s} {'fields ok':>10s} {'acc':>4s} {'rev':>4s} {'miss':>4s} {'wCaught':>7s} {'wAccept':>7s} {'review/sub':>10s} {'READY':>5s} {'falseREADY':>10s} {'uploadRej':>9s}"
    print(header)
    tot = Counter()
    for name, g in G.items():
        ok = g["CORRECT_ACCEPTED"] + g["CORRECT_REVIEW"] + g["CORRECT_ABSENT"]
        tot.update(g)
        rps = g["review_fields"] / g["submissions"] if g["submissions"] else 0
        print(f"{name:26s} {g['submissions']:4d} {g['type_correct']:5d}/{g['type_docs']:<7d} {ok:4d}/{g['fields']:<5d} {g['CORRECT_ACCEPTED']:4d} {g['CORRECT_REVIEW']:4d} {g['MISSING']:4d} {g['WRONG_CAUGHT']:7d} {g['WRONG_ACCEPTED']:7d} {rps:10.2f} {g['status_READY']:5d} {g['false_ready']:10d} {g['upload_rejected_docs']:9d}")
    for label, groups in (("G1-G5 variants (excl. G3b)", [k for k in G if k[:2] in ("G1", "G2", "G3", "G4", "G5") and not k.startswith("G3b")]),):
        t = Counter()
        for k in groups:
            t.update(G[k])
        ok = t["CORRECT_ACCEPTED"] + t["CORRECT_REVIEW"] + t["CORRECT_ABSENT"]
        print(f"\n{label}: fields correct {fmt_ci(ok, t['fields'])}; wrong accepted {fmt_ci(t['WRONG_ACCEPTED'], t['CORRECT_ACCEPTED'] + t['WRONG_ACCEPTED'])}; false READY {fmt_ci(t['false_ready'], t['submissions'])}; type {fmt_ci(t['type_correct'], t['type_docs'])}")
    g0 = G["G0_real_photo"]
    print("\nG0 fields correct", fmt_ci(g0["CORRECT_ACCEPTED"] + g0["CORRECT_REVIEW"] + g0["CORRECT_ABSENT"], g0["fields"]), "| wrong accepted", g0["WRONG_ACCEPTED"], "| false READY", g0["false_ready"], "/", g0["submissions"])
    print("review reasons for correct values, per group:")
    for k, c in reasons.items():
        print(" ", k, dict(c.most_common(6)))
    print("status mix per group:", {k: {s[7:]: v for s, v in g.items() if s.startswith("status_")} for k, g in G.items()})
    print("errors:", Counter((e["kind"], str(e.get("code"))) for e in errors))
    print("expiry:", json.dumps(expiry, ensure_ascii=False))
    (a.run / "SCORE_FRESH.json").write_text(json.dumps({"groups": {k: dict(v) for k, v in G.items()}, "rows": rows, "gpa_rows": gpa_rows, "errors": errors, "expiry": expiry,
                                                        "reasons": {k: dict(v) for k, v in reasons.items()}}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("scored submissions:", seen, "of", len(subs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
