"""Score a run_real.py --submissions run of the mentor's business set against the owner-confirmed gold (private inputs).

    python3 score_business.py --run RESULTS_DIR --dir data/private_real/business [--standard]

Masked counts only. Writes SCORE_BUSINESS.json next to the run (private).
Field outcomes as in score_fresh.py. Company names are compared after dropping legal-form markers, parenthesised
Latin text and spaces (scoring only: the statuses are reported exactly as the system produced them).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_variants_real import fmt_ci  # noqa: E402

NAME_FIELDS = {"company_name", "workplace_name"}


def norm(field: str, v) -> str | None:
    if v is None:
        return None
    s = unicodedata.normalize("NFKC", str(v))
    if field in NAME_FIELDS:
        s = re.sub(r"\([A-Za-z0-9 .&-]+\)", "", s)
        s = s.replace("주식회사", "").replace("(주)", "").replace("㈜", "")
    if field == "business_registration_number":
        return re.sub(r"\D", "", s)
    return "".join(s.split())


def outcome(field: str, expected, f: dict) -> tuple[str, bool]:
    machine, effective = f.get("machine_value"), f.get("value")
    accepted = effective is not None
    exp = norm(field, expected)
    if accepted and norm(field, effective) != exp:
        return "WRONG_ACCEPTED", True
    if machine is None:
        return "MISSING", False
    if norm(field, machine) != exp:
        return "WRONG_CAUGHT", False
    return ("CORRECT_ACCEPTED" if accepted else "CORRECT_REVIEW"), False


def reason(f: dict) -> str:
    return str((f.get("auto_acceptance") or {}).get("reason") or f.get("evidence_state") or "unknown")


def scored_fields(gold_doc: dict) -> dict:
    fields = {k: v["value"] for k, v in gold_doc["fields"].items() if v["state"] == "KNOWN_VALUE"}
    obs = gold_doc.get("observations", {})
    if gold_doc["document_type"] != "UNKNOWN" and obs.get("issue_date"):
        fields["issue_date"] = obs["issue_date"][:10]
    if gold_doc["document_type"] == "BUSINESS_REGISTRATION_CERTIFICATE" and obs.get("representative"):
        fields["representative_name"] = obs["representative"]
    return fields


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    gold = json.loads((a.dir / "gold.json").read_text(encoding="utf-8"))["documents"]
    kinds = {d["document"]: d["source_kind"] for d in json.loads((a.dir / "manifest.json").read_text(encoding="utf-8"))["files"]}
    subs = json.loads((a.dir / "SUBMISSIONS.json").read_text(encoding="utf-8"))
    G = defaultdict(Counter)
    reasons = defaultdict(Counter)
    types = {}  # (group, recipe, file) -> (predicted, expected)
    negatives, notation, errors, rows = [], [], [], []
    for sub in subs:
        path = a.run / f"sub_{sub['id']}.json"
        if not path.exists():
            continue
        run = json.loads(path.read_text(encoding="utf-8"))
        status = run["verification"].get("status")
        codes = sorted({i.get("code") for i in run["verification"].get("issues", []) if i.get("code")})
        notices = sorted({i.get("code") for i in run["verification"].get("notices", []) if i.get("code")})
        gname = sub["group"] if sub["group"] != "G0_original" else "G0_" + ("std" if sub["workflow"] == "standard" else "reduced")
        g = G[gname]
        docmap = {Path(k).name: v for k, v in sub["docs"].items()}
        wrong_eff = 0
        for rec in run["documents"]:
            if rec.get("upload_status") != 201 or rec.get("processing_error_code"):
                errors.append({"sub": sub["id"], "file": rec["file"], "upload": rec.get("upload_status"), "code": rec.get("processing_error_code")})
            did = docmap.get(rec["file"])
            if did is None:
                continue
            gd = gold[did]
            types[(sub["group"], sub["recipe"], did)] = (rec.get("predicted_document_type"), gd["document_type"])
            if sub["kind"] != "valid" or sub["workflow"] != "reduced":
                continue
            fields = rec.get("fields") or {}
            g["docs_in_valid"] += 1
            sk = kinds.get(did, "?")
            for field, expected in scored_fields(gd).items():
                f = fields.get(field) or {}
                o, eff_wrong = outcome(field, expected, f)
                g["fields"] += 1
                g[o] += 1
                g["review_fields"] += o in ("MISSING", "CORRECT_REVIEW", "WRONG_CAUGHT")
                wrong_eff += eff_wrong
                if sub["group"] == "G0_original":
                    G["G0_" + sk][o] += 1
                    G["G0_" + sk]["fields"] += 1
                if o == "CORRECT_REVIEW":
                    reasons[gname][reason(f)] += 1
                rows.append({"sub": sub["id"], "group": sub["group"], "doc": did, "field": field, "outcome": o})
        if sub["kind"] == "negative" or sub["kind"] == "valid" or sub["kind"] == "multipage":
            g["subs_" + sub["kind"]] += 1
            g["status_" + sub["kind"] + "_" + str(status)] += 1
            false_ready = status == "READY" and (sub["kind"] == "negative" or wrong_eff > 0)
            g["false_ready"] += false_ready
            g["ready"] += status == "READY"
            g["decided_without_person"] += status in ("READY", "NEEDS_CORRECTION")
        if sub["kind"] == "negative":
            negatives.append({"id": sub["id"], "group": sub["group"], "case": sub["case"], "workflow": sub["workflow"], "status": status, "codes": codes, "notices": notices})
        if sub["kind"] == "valid":
            for issue in run["verification"].get("issues", []):
                if issue.get("field_name") in NAME_FIELDS or issue.get("code") == "INFORMATION_MISMATCH":
                    notation.append({"sub": sub["id"], "group": sub["group"], "workflow": sub["workflow"], "code": issue.get("code"), "field": issue.get("field_name"),
                                     "doc": issue.get("document_type"), "related": issue.get("related_document_type"), "effect": issue.get("status_effect")})
    # document types, one count per (group, recipe, document id)
    for (group, recipe, did), (pred, exp) in types.items():
        gname = group if group != "G0_original" else "G0_reduced"
        G[gname]["type_files"] += 1
        G[gname]["type_ok"] += pred == exp
        if exp == "UNKNOWN":
            G[gname]["lookalike_files"] += 1
            G[gname]["lookalike_not_accepted_as_national_tax"] += pred != "NATIONAL_TAX_PAYMENT_CERTIFICATE"
        if group == "G0_original":
            sk = kinds.get(did, "?")
            G["G0_" + sk]["type_files"] += 1
            G["G0_" + sk]["type_ok"] += pred == exp
    order = ["G0_digital", "G0_scan", "G0_reduced", "G0_std", "G1_scan200", "G2_scan_quality", "G3_geometry", "G3b_known_limit", "G4_photo_style", "G5_formats"]
    print(f"{'group':18s} {'type files':>12s} {'fields correct':>26s} {'acc':>4s} {'rev':>4s} {'miss':>4s} {'wCaught':>7s} {'wAccept':>7s} {'valid subs':>10s} {'negatives':>9s} {'falseREADY':>10s}")
    for name in order:
        g = G.get(name)
        if not g:
            continue
        ok = g["CORRECT_ACCEPTED"] + g["CORRECT_REVIEW"]
        print(f"{name:18s} {fmt_ci(g['type_ok'], g['type_files']) if g['type_files'] else 'n/a':>12s} {fmt_ci(ok, g['fields']) if g['fields'] else 'n/a':>26s} {g['CORRECT_ACCEPTED']:4d} {g['CORRECT_REVIEW']:4d} {g['MISSING']:4d} {g['WRONG_CAUGHT']:7d} {g['WRONG_ACCEPTED']:7d} {g['subs_valid']:10d} {g['subs_negative']:9d} {g['false_ready']:10d}")
    print("reasons:", {k: dict(v.most_common(5)) for k, v in reasons.items()})
    print("errors:", Counter((e["upload"], e["code"]) for e in errors))
    (a.run / "SCORE_BUSINESS.json").write_text(json.dumps({"groups": {k: dict(v) for k, v in G.items()}, "negatives": negatives, "notation": notation, "errors": errors, "reasons": {k: dict(v) for k, v in reasons.items()}, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
