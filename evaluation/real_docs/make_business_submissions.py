"""Build gold.json (private, from the owner-confirmed draft) and SUBMISSIONS.json for the mentor's business documents.

    python3 make_business_submissions.py --dir data/private_real/business --confirmed-on YYYY-MM-DD   (writes gold.json)
    python3 make_business_submissions.py --dir data/private_real/business --draft-only                  (SUBMISSIONS.json + masked listing; no gold.json)

Contains no document content. Submissions follow the set's pairing rule: every submission is built from files of the SAME group and recipe.
Most run on the workflow without the 중소기업확인서 (the set has none); the originals also run on the standard workflow.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

TYPE = {"BUSINESS_REGISTRATION": "BUSINESS_REGISTRATION_CERTIFICATE", "NATIONAL_TAX_CERT": "NATIONAL_TAX_PAYMENT_CERTIFICATE",
        "SOCIAL_INSURANCE_CERT": "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE", "LOCAL_TAX_CERT": "UNKNOWN"}
NAME_FIELD = {"SOCIAL_INSURANCE_CERT": "workplace_name"}


def mask(value: str) -> str:
    return value if len(value) <= 2 else value[0] + "*" * (len(value) - 2) + value[-1]


def mask_number(value: str) -> str:
    keep = [i for i, c in enumerate(value) if c.isdigit()]
    tail = set(keep[-2:]) | set(keep[:1])
    return "".join(c if (not c.isdigit() or i in tail) else "*" for i, c in enumerate(value))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--draft", default="gold_DRAFT.json")
    ap.add_argument("--confirmed-on", default=None)
    a = ap.parse_args()
    manifest = json.loads((a.dir / "manifest.json").read_text(encoding="utf-8"))
    draft = json.loads((a.dir / a.draft).read_text(encoding="utf-8"))
    docs = draft["documents"]
    subs_def = {k: v for k, v in draft["submissions"].items() if isinstance(v, dict)}

    gold = {"status": "CONFIRMED by the owner" if a.confirmed_on else "DRAFT (not confirmed: do not score)", "confirmed_on": a.confirmed_on, "documents": {}}
    for doc_id, d in docs.items():
        kind = d["doc_type"]
        fields: dict = {}
        if kind != "LOCAL_TAX_CERT":
            fields[NAME_FIELD.get(kind, "company_name")] = {"state": "KNOWN_VALUE", "value": d["company_name"]}
            fields["business_registration_number"] = {"state": "KNOWN_VALUE", "value": d["business_number"]}
            if "valid_until" in d:
                fields["valid_until"] = {"state": "KNOWN_VALUE", "value": d["valid_until"]}
        gold["documents"][doc_id] = {"document_type": TYPE[kind], "fields": fields, "observations": {k: v for k, v in d.items() if k in ("issue_date", "representative", "opening_date", "corporate_reg_no", "issue_number", "receipt_date")}}
    target = a.dir / ("gold.json" if a.confirmed_on else "gold_pending.json")
    target.write_text(json.dumps(gold, ensure_ascii=False, indent=1), encoding="utf-8")

    where = defaultdict(dict)  # (group, recipe) -> doc id -> file
    for f in manifest["files"]:
        stem = f["file"].split("/")[-1]
        if f["document"].startswith("multipage") or "multipage" in stem:
            continue
        recipe = stem.split("__", 1)[1] if "__" in stem else Path(stem).suffix.lstrip(".")
        where[(f["group"], recipe)][f["document"]] = f["file"]
    subs = []
    for (group, recipe), files in where.items():
        key = f"{group.split('_')[0]}_{recipe}".replace("+", "p").replace("-", "m").replace(".", "_")
        for sid, sd in subs_def.items():
            if not all(d in files for d in sd["docs"]):
                continue
            base = {"group": group, "recipe": recipe, "files": [files[d] for d in sd["docs"]], "docs": {files[d]: d for d in sd["docs"]},
                    "eval_date": sd["check_date"], "kind": "negative" if sid.startswith("N") else "valid", "case": sid.split("_")[0], "expect": sd["expect"]}
            subs.append({**base, "id": f"{key}_{sid.split('_')[0]}", "workflow": "reduced"})
            if group == "G0_original":
                subs.append({**base, "id": f"{key}_{sid.split('_')[0]}_std", "workflow": "standard"})
    for f in manifest["files"]:
        stem = f["file"].split("/")[-1]
        if "multipage" in stem:
            fam = "F21" if "F21" in stem else "RS"
            date = "2026-10-30" if fam == "F21" else "2023-10-07"
            subs.append({"id": f"m_{fam}", "group": f["group"], "recipe": "multipage", "files": [f["file"]], "docs": {}, "eval_date": date, "kind": "multipage",
                         "case": "M", "expect": "judged by status only", "workflow": "reduced"})
    ids = [s["id"] for s in subs]
    assert len(ids) == len(set(ids))
    (a.dir / "SUBMISSIONS.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1), encoding="utf-8")
    # masked listing for the owner's confirmation
    lines = ["| id | type | name | number | issue date | valid until |", "|---|---|---|---|---|---|"]
    for doc_id, d in docs.items():
        lines.append(f"| {doc_id} | {TYPE[d['doc_type']]} | {mask(d['company_name'])} | {mask_number(d['business_number'])} | {d.get('issue_date', d.get('receipt_date', '-'))} | {d.get('valid_until', '-')} |")
    (a.dir / "gold_masked.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    kinds = defaultdict(int)
    for s in subs:
        kinds[(s["kind"], s["workflow"])] += 1
    print("submissions", len(subs), dict(kinds), "| recipes", len(where))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
