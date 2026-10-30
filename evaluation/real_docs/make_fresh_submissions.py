"""Build SUBMISSIONS.json and gold.json (private outputs) for the fresh-capture test set from its manifest.json.

    python3 make_fresh_submissions.py --dir data/private_real/fresh --draft gold_DRAFT.json --confirmed-on 2026-10-30

Contains no document content: values come from the owner-confirmed draft and are written only under --dir (git-ignored).
Pairs: R45 = enrollment + transcript_45, R43 = enrollment + transcript_43, matched by group and recipe.
G1 pairs carry the expiry checks as extra inspection dates (same upload, re-verified; no second OCR pass).
"""
from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path

MAIN_DATE = "2026-11-02"
EXPIRY_DATES = ["2027-01-28", "2027-01-29"]  # last valid day (issue 2026-10-30 + 90 days), first expired day
IPHONE = {"enrollment": "IMG_4198.jpg", "transcript_45": "IMG_4196.jpg", "transcript_43": "IMG_4197.jpg"}
GROUP_ORDER = ["G0_real_photo", "G0b_iphone_originals", "G1_flat", "G2_scan_quality", "G3_geometry",
               "G3b_known_limit", "G4_photo_style", "G5_formats"]


def recipe(file: str, document: str) -> str:
    stem = Path(file).stem
    ext = Path(file).suffix.lstrip(".")
    return (stem.split("__", 1)[1] + "_" + ext) if "__" in stem else ext


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--draft", default="gold_DRAFT.json")
    ap.add_argument("--confirmed-on", required=True)
    a = ap.parse_args()
    manifest = json.loads((a.dir / "manifest.json").read_text(encoding="utf-8"))
    draft = json.loads((a.dir / a.draft).read_text(encoding="utf-8"))["documents"]

    gold = {"status": "CONFIRMED by the owner against the paper documents", "confirmed_on": a.confirmed_on, "documents": {}, "observations": {}}
    for name, d in draft.items():
        fields = {k: {"state": "KNOWN_VALUE", "value": d[k]} for k in ("student_name", "university_name", "issue_date") if d.get(k)}
        if name == "enrollment":
            fields["department"] = {"state": "KNOWN_VALUE", "value": d["department"]}
            fields["student_id"] = {"state": "VERIFIED_ABSENT"}
        else:
            fields["student_id"] = {"state": "KNOWN_VALUE", "value": d["student_id"]}
            fields["gpa"] = {"state": "KNOWN_VALUE", "value": d["gpa"]}
            fields["gpa_scale"] = {"state": "KNOWN_VALUE", "value": d["gpa_scale"]}
        gold["documents"][name] = {"document_type": d["doc_type"], "fields": fields}
        gold["observations"][name] = {k: d.get(k) for k in ("percent", "certificate_no", "major", "double_major", "total_credits", "semesters", "observations", "department", "birth_date") if k in d}
    (a.dir / "gold.json").write_text(json.dumps(gold, ensure_ascii=False, indent=1), encoding="utf-8")

    files = manifest["files"]
    by = OrderedDict((g, {}) for g in GROUP_ORDER)
    for f in files:
        if f["document"] in ("enrollment", "transcript_45", "transcript_43"):
            by[f["group"]].setdefault(recipe(f["file"], f["document"]), {})[f["document"]] = f["file"]
    for doc, fn in IPHONE.items():
        by["G0b_iphone_originals"].setdefault("iphone", {})[doc] = f"G0b_iphone_originals/{fn}"

    subs = []
    for group, recipes in by.items():
        for rec, docs in recipes.items():
            for tag, tr in (("R45", "transcript_45"), ("R43", "transcript_43")):
                s = {"id": f"p_{group.split('_')[0]}_{rec}_{tag}".replace("+", "p").replace("-", "m"), "group": group, "kind": "pair", "scale": tr[-2:],
                     "files": [docs["enrollment"], docs[tr]], "docs": {docs["enrollment"]: "enrollment", docs[tr]: tr},
                     "eval_date": MAIN_DATE, "expected": "type/fields as gold"}
                if group == "G1_flat":
                    s["extra_eval_dates"] = EXPIRY_DATES
                subs.append(s)
    for f in files:
        if f["document"].startswith("enrollment+"):
            subs.append({"id": "m_" + f["document"].replace("+", "_"), "group": "G5_formats", "kind": "multipage", "files": [f["file"]], "docs": {},
                         "eval_date": MAIN_DATE, "expected": "judged by status only"})
    for group, recipes in by.items():
        for rec, docs in recipes.items():
            for doc, file in docs.items():
                subs.append({"id": f"s_{group.split('_')[0]}_{rec}_{doc}".replace("+", "p").replace("-", "m"), "group": group, "kind": "single",
                             "files": [file], "docs": {file: doc}, "eval_date": MAIN_DATE, "expected": "type/fields as gold"})
    ids = [s["id"] for s in subs]
    assert len(ids) == len(set(ids)), "duplicate submission ids"
    (a.dir / "SUBMISSIONS.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1), encoding="utf-8")
    kinds = {k: sum(s["kind"] == k for s in subs) for k in ("pair", "multipage", "single")}
    print("submissions", len(subs), kinds, "| files", len(files), "+3 iPhone originals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
