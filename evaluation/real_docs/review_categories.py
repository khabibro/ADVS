"""Why does a field or a submission need a person? Categorise every 확인 필요 case (private inputs, masked output).

    python3 review_categories.py --private data/private_real --arm results/final/off --biz results/biz_frozen \
        --out-json data/private_real/results/review_categories.json

Categories (one primary cause per case):
  C1  OCR 인식           the value was not read, was misread, or the reading is not certain enough
  C2  항목 구분/필드 매핑   the text is on the page but the extractor did not take it, took another text, or
                         took it only by position (no label)
  C3  문서 간 비교         the value is right but no independent source confirms it, or sources disagree
  C4  문서 분류           the document type is wrong, unknown or doubtful
  C5  안전 정책           a policy withholds the decision although value and type are right

Units: a field (gold field not auto-accepted) and a submission (not READY). Gold values are compared in
memory only; the output holds counts and reason codes, never a value.
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
from score_business import norm as norm_business  # noqa: E402
from score_business import scored_fields  # noqa: E402
from score_real import norm as norm_student  # noqa: E402
from score_variants_real import TYPE_BY_KEY, doc_key, wilson  # noqa: E402

CATEGORIES = ["C1", "C2", "C3", "C4", "C5"]
CATEGORY_NAME = {
    "C1": "OCR 인식",
    "C2": "항목 구분/필드 매핑",
    "C3": "문서 간 비교",
    "C4": "문서 분류",
    "C5": "안전 정책",
}

#: (reason code from the auto-accept policy) -> (category, sub-cause)
REASON_MAP = {
    "CONFIDENCE_BELOW_FLOOR": ("C1", "confidence below the floor"),
    "NEAR_DECISION_BOUNDARY": ("C1", "confidence near the decision boundary"),
    "SECOND_PASS_CONTRADICTS_NAME": ("C1", "second reading disagrees (name-like text)"),
    "SECOND_PASS_DISAGREES": ("C1", "second reading disagrees"),
    "ARITHMETIC_MISMATCH": ("C1", "arithmetic check fails (digit uncertain)"),
    "SEMANTIC_INFERENCE": ("C2", "value taken by position, no label"),
    "NO_INDEPENDENT_CONFIRMATION": ("C3", "no second document confirms the value"),
    "DISAGREES_WITH_OTHER_DOCUMENT": ("C3", "another document reads it differently"),
    "GRADING_SCALE_MISMATCH": ("C3", "grading scale differs between documents"),
    "NO_RULE_FOR_FIELD": ("C5", "no auto-accept rule for this field"),
}
FORMAT_PREFIX = "FORMAT_"
CLASSIFICATION_CODES = {
    "CLASSIFICATION_REQUIRES_REVIEW",
    "UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW",
    "MULTIPLE_DOCUMENTS_IN_FILE",
    "TEXT_LAYER_MISMATCH",
}
#: codes that do not come from the accuracy of a field or the document type
NOT_ACCURACY = {"MISSING_REQUIRED_DOCUMENT", "EXPIRED_DOCUMENT", "DUPLICATE_DOCUMENT"}
DATE_RE = re.compile(r"(20\d{2})\D{1,3}(\d{1,2})\D{1,3}(\d{1,2})")
PHOTO_GROUPS = ("G0", "G0b", "G4", "phone_photo", "G4_photo_style")


def compact(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).split())


def present_in_text(field: str, gold: str, text: str) -> bool:
    """Is the gold value readable anywhere in the page text? (in-memory comparison only)"""
    gold = unicodedata.normalize("NFKC", str(gold))
    if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", gold):
        want = tuple(int(p) for p in gold.split("-"))
        return any(
            tuple(int(g) for g in m.groups()) == want for m in DATE_RE.finditer(unicodedata.normalize("NFKC", text))
        )
    if field in ("business_registration_number", "corporate_registration_number"):
        digits = re.sub(r"\D", "", gold)
        return bool(digits) and digits in re.sub(r"\D", "", text)
    needle = compact(re.sub(r"\([A-Za-z0-9 .&-]+\)", "", gold))
    needle = needle.replace("주식회사", "").replace("(주)", "").replace("㈜", "")
    return bool(needle) and needle in compact(text).replace("주식회사", "").replace("㈜", "")


def field_outcome(norm, name: str, expected, f: dict) -> str:
    machine, effective = f.get("machine_value"), f.get("value")
    if effective is not None and norm(name, effective) != norm(name, expected):
        return "WRONG_ACCEPTED"
    if machine is None:
        return "MISSING"
    if norm(name, machine) != norm(name, expected):
        return "WRONG_CAUGHT"
    return "CORRECT_ACCEPTED" if effective is not None else "CORRECT_REVIEW"


def ocr_text(run_dir: Path, sub_id: str) -> dict[str, str]:
    path = run_dir / f"sub_{sub_id}_ocr.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {Path(name).name: "\n".join(p.get("text", "") for p in pages) for name, pages in data.items()}


def ocr_source(run_dir: Path, sub_id: str) -> dict[str, str]:
    path = run_dir / f"sub_{sub_id}_ocr.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        Path(name).name: ("digital" if any(p["metadata"].get("source") != "ocr" for p in pages) else "ocr")
        for name, pages in data.items()
    }


def source_of(sources: dict[str, str], file: str) -> str:
    """A PDF with no OCR record was read from its text layer."""
    if file in sources:
        return sources[file]
    return "digital" if file.lower().endswith(".pdf") else "ocr"


def medium(group: str, source: str) -> str:
    if source == "digital":
        return "digital"
    return "photo" if group.split("_")[0] in PHOTO_GROUPS or group in PHOTO_GROUPS else "scan"


def categorise_field(outcome: str, f: dict, field: str, gold, text: str, type_ok: bool) -> tuple[str, str]:
    if not type_ok:
        return "C4", "document typed wrongly or unknown: field not extracted"
    aa = f.get("auto_acceptance") or {}
    reason = aa.get("reason")
    present = present_in_text(field, gold, text) if text else False
    if outcome == "MISSING":
        return ("C2", "value is in the page text but was not extracted") if present else ("C1", "value not read by the OCR")
    if outcome == "WRONG_CAUGHT":
        return ("C2", "another text taken instead of the value") if present else ("C1", "value misread (caught)")
    if reason in REASON_MAP:
        return REASON_MAP[reason]
    if isinstance(reason, str) and reason.startswith(FORMAT_PREFIX):
        return "C5", "format/plausibility check withholds the value"
    return "C1", "OCR confirmation required (no specific reason recorded)"


def load_runs(args) -> list[dict]:
    private = Path(args.private)
    arm = private / args.arm
    subs: list[dict] = []

    # fresh
    fresh_gold = json.loads((private / "fresh/gold.json").read_text(encoding="utf-8"))["documents"]
    for sub in json.loads((private / "fresh/SUBMISSIONS.json").read_text(encoding="utf-8")):
        path = arm / "fresh" / f"sub_{sub['id']}.json"
        if sub["kind"] != "pair" or not path.exists():
            continue
        run = json.loads(path.read_text(encoding="utf-8"))
        texts, sources = ocr_text(arm / "fresh", sub["id"]), ocr_source(arm / "fresh", sub["id"])
        docmap = {Path(k).name: v for k, v in sub["docs"].items()}
        docs = []
        for rec in run["documents"]:
            label = docmap.get(rec["file"])
            if label is None or rec.get("upload_status") != 201:
                continue
            gd = fresh_gold[label]
            fields = {}
            for name, spec in gd["fields"].items():
                if spec["state"] == "VERIFIED_ABSENT":
                    continue
                fields[name] = (spec["value"], rec["fields"].get(name) or {}, norm_student_fresh)
            docs.append(dict(file=rec["file"], type_ok=rec.get("predicted_document_type") == gd["document_type"],
                             medium=medium(sub["group"], source_of(sources, rec["file"])), text=texts.get(rec["file"], ""),
                             fields=fields, doctype=gd["document_type"]))
        subs.append(dict(family="fresh", id=sub["id"], group=sub["group"], kind="valid", run=run, docs=docs))

    # seeds
    gold = json.loads((private / "gold.json").read_text(encoding="utf-8"))["documents"]
    gold_by_type = {g["document_type"]: g for g in gold.values()}
    for seed in ("seedA", "seedB"):
        d = arm / seed
        for sub in json.loads((private / f"variants/{seed}/SUBMISSIONS.json").read_text(encoding="utf-8")):
            path = d / f"sub_{sub['id']}.json"
            if not path.exists():
                continue
            run = json.loads(path.read_text(encoding="utf-8"))
            texts, sources = ocr_text(d, sub["id"]), ocr_source(d, sub["id"])
            docs = []
            for rec in run["documents"]:
                key = doc_key(rec["file"])
                if key is None or "combined" in rec["file"] or (sub["id"] == "n_identity_mismatch" and key == "성적증명서"):
                    continue  # multi-page / fictional documents are judged by status only
                etype = TYPE_BY_KEY[key]
                fields = {n: (s["value"], rec["fields"].get(n) or {}, norm_student_fresh)
                          for n, s in gold_by_type[etype]["fields"].items() if s["state"] != "VERIFIED_ABSENT"}
                docs.append(dict(file=rec["file"], type_ok=rec.get("predicted_document_type") == etype,
                                 medium=medium(sub["group"], source_of(sources, rec["file"])),
                                 text=texts.get(rec["file"], ""), fields=fields, doctype=etype))
            kind = "negative" if sub["group"] == "negative" else "valid"
            subs.append(dict(family=seed, id=sub["id"], group=sub["group"], kind=kind, run=run, docs=docs))

    # business (reduced checklist, valid and negative submissions)
    if args.biz:
        bdir = private / args.biz
        bgold = json.loads((private / "business/gold.json").read_text(encoding="utf-8"))["documents"]
        kinds = {d["document"]: d["source_kind"]
                 for d in json.loads((private / "business/manifest.json").read_text(encoding="utf-8"))["files"]}
        for sub in json.loads((private / "business/SUBMISSIONS.json").read_text(encoding="utf-8")):
            path = bdir / f"sub_{sub['id']}.json"
            if not path.exists() or sub["workflow"] != "reduced":
                continue
            run = json.loads(path.read_text(encoding="utf-8"))
            texts, sources = ocr_text(bdir, sub["id"]), ocr_source(bdir, sub["id"])
            docmap = {Path(k).name: v for k, v in sub["docs"].items()}
            docs = []
            for rec in run["documents"]:
                did = docmap.get(rec["file"])
                if did is None or rec.get("upload_status") != 201:
                    continue
                gd = bgold[did]
                fields = {n: (v, rec["fields"].get(n) or {}, norm_business) for n, v in scored_fields(gd).items()}
                docs.append(dict(file=rec["file"], type_ok=rec.get("predicted_document_type") == gd["document_type"],
                                 medium=medium(sub["group"], source_of(sources, rec["file"])),
                                 text=texts.get(rec["file"], ""), fields=fields, doctype=gd["document_type"]))
            subs.append(dict(family="business", id=sub["id"], group=sub["group"],
                             kind="negative" if sub["kind"] == "negative" else "valid", run=run, docs=docs,
                             case=sub.get("case")))
    return subs


def norm_student_fresh(name, value):
    return norm_student(name, value)


def analyse(subs: list[dict]) -> dict:
    items: list[dict] = []
    sub_rows: list[dict] = []
    for sub in subs:
        status = sub["run"]["verification"].get("status")
        issue_codes = sorted({i.get("code") for i in sub["run"]["verification"].get("issues", []) if i.get("code")})
        blockers = set()
        wrong_effective = False
        for doc in sub["docs"]:
            for name, (expected, f, norm) in doc["fields"].items():
                outcome = field_outcome(norm, name, expected, f)
                if outcome == "WRONG_ACCEPTED":
                    wrong_effective = True
                if outcome == "CORRECT_ACCEPTED":
                    continue
                cat, cause = categorise_field(outcome, f, name, expected, doc["text"], doc["type_ok"])
                unfixable = outcome in ("WRONG_CAUGHT",) or (outcome == "MISSING" and cat in ("C1",))
                items.append(dict(family=sub["family"], sub=sub["id"], group=sub["group"], medium=doc["medium"],
                                  doctype=doc["doctype"], field=name, outcome=outcome, category=cat, cause=cause,
                                  kind=sub["kind"]))
                blockers.add((doc["file"], name, cat, unfixable))
            if not doc["type_ok"]:
                blockers.add((doc["file"], "__type__", "C4", True))
        classification = [c for c in issue_codes if c in CLASSIFICATION_CODES]
        sub_rows.append(dict(family=sub["family"], sub=sub["id"], group=sub["group"], kind=sub["kind"], status=status,
                             issue_codes=issue_codes, blockers=[list(b) for b in blockers],
                             classification_issues=classification, wrong_effective=wrong_effective,
                             medium=sorted({d["medium"] for d in sub["docs"]})))
    return {"items": items, "subs": sub_rows}


def if_fixed(sub_rows: list[dict], fixed: set[str]) -> dict:
    """Valid submissions that would have no blocker left if the given categories were resolved correctly.
    A field read wrongly (caught) or not read at all (C1) stays a blocker: it cannot be accepted without a person,
    and a wrong value is never counted as fixed. Submissions blocked by anything outside accuracy are excluded."""
    would, total = 0, 0
    for s in sub_rows:
        if s["kind"] != "valid":
            continue
        total += 1
        if s["status"] == "READY":
            would += 1
            continue
        if set(s["issue_codes"]) & NOT_ACCURACY:
            continue
        remaining = False
        for _file, _name, cat, unfixable in s["blockers"]:
            if unfixable or cat not in fixed:
                remaining = True
        if s["classification_issues"] and "C4" not in fixed:
            remaining = True
        if not remaining:
            would += 1
    return {"valid_submissions": total, "ready_if_fixed": would}


def remaining_blockers(sub_rows: list[dict], fixed_causes: set[tuple[str, str]], items: list[dict]) -> Counter:
    """For valid, non-READY submissions free of non-accuracy blockers: how many blocking fields would remain if the
    given (category, cause) pairs were resolved correctly. Fields read wrongly or not at all stay."""
    cause_of = {(i["family"], i["sub"], i["field"], i["doctype"]): (i["category"], i["cause"]) for i in items}
    del cause_of  # per-field cause is keyed by sub in the loop below
    by_sub: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for i in items:
        by_sub[(i["family"], i["sub"])].append(i)
    dist: Counter = Counter()
    for s in sub_rows:
        if s["kind"] != "valid" or s["status"] == "READY" or set(s["issue_codes"]) & NOT_ACCURACY:
            continue
        left = sum(
            1
            for i in by_sub[(s["family"], s["sub"])]
            if (i["category"], i["cause"]) not in fixed_causes or i["outcome"] == "WRONG_CAUGHT"
        )
        dist["n"] += 1
        dist["left"] += left
        dist["zero"] += left == 0
        dist["one"] += left == 1
    return dist


def report(result: dict) -> dict:
    items, sub_rows = result["items"], result["subs"]
    by = lambda keyf: Counter(keyf(i) for i in items)  # noqa: E731
    out = {
        "fields_total": len(items),
        "by_category": dict(by(lambda i: i["category"])),
        "by_category_family": {fam: dict(Counter(i["category"] for i in items if i["family"] == fam))
                               for fam in sorted({i["family"] for i in items})},
        "by_category_medium": {m: dict(Counter(i["category"] for i in items if i["medium"] == m))
                               for m in ("digital", "scan", "photo")},
        "by_cause": [(k, v) for k, v in Counter((i["category"], i["cause"]) for i in items).most_common()],
        "by_field": {f"{c}:{f}": n for (c, f), n in by(lambda i: (i["category"], i["field"])).most_common(40)},
        "submissions": {"total": len(sub_rows),
                        "valid_not_ready": sum(1 for s in sub_rows if s["kind"] == "valid" and s["status"] != "READY"),
                        "negative_ready": sum(1 for s in sub_rows if s["kind"] == "negative" and s["status"] == "READY"),
                        "ready": sum(1 for s in sub_rows if s["status"] == "READY"),
                        "wrong_effective": sum(1 for s in sub_rows if s["wrong_effective"])},
        "if_fixed": {},
    }
    for label, cats in [("none", set()), *[(c, {c}) for c in CATEGORIES], ("C2+C3", {"C2", "C3"}), ("C2+C3+C5", {"C2", "C3", "C5"}),
                        ("C1..C5", set(CATEGORIES))]:
        out["if_fixed"][label] = if_fixed(sub_rows, cats)
    fam = {}
    for f in sorted({s["family"] for s in sub_rows}):
        rows = [s for s in sub_rows if s["family"] == f]
        fam[f] = {c: if_fixed(rows, {c} if c != "none" else set()) for c in ["none", *CATEGORIES]}
        fam[f]["C2+C3+C5"] = if_fixed(rows, {"C2", "C3", "C5"})
    out["if_fixed_by_family"] = fam
    # blocker-category combinations per not-ready valid submission
    combo = Counter()
    for s in sub_rows:
        if s["kind"] == "valid" and s["status"] != "READY":
            combo[tuple(sorted({b[2] for b in s["blockers"]} | ({"C4"} if s["classification_issues"] else set())))] += 1
    cause_counts = Counter((i["category"], i["cause"]) for i in items)
    all_causes = set(cause_counts)
    out["remaining_blockers_after_fixing"] = {
        "nothing": dict(remaining_blockers(sub_rows, set(), items)),  # n, left (blocking fields), zero, one
        "every cause": dict(remaining_blockers(sub_rows, all_causes, items)),
        **{f"{c} {cause}": dict(remaining_blockers(sub_rows, {(c, cause)}, items)) for (c, cause), _ in cause_counts.most_common(10)},
    }
    out["submission_blocker_combinations"] = [("+".join(k) or "other", v) for k, v in combo.most_common(12)]
    # wilson share of each category among fields
    n = len(items)
    out["category_share_wilson"] = {c: [round(100 * x, 1) for x in wilson(out["by_category"].get(c, 0), n)] for c in CATEGORIES}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--private", default="data/private_real")
    ap.add_argument("--arm", default="results/final/off")
    ap.add_argument("--biz", default="results/biz_frozen")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()
    result = analyse(load_runs(args))
    rep = report(result)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    if args.out_json:
        Path(args.out_json).write_text(
            json.dumps({"report": rep, "items": result["items"], "subs": result["subs"]}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
