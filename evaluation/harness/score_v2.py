"""Scorer v2 for the ADVS evaluation corpora (development set and hold-out).

Frozen at Phase D step D1; its SHA-256 is recorded in every report. score_variants.py
(v1) is untouched.

Comparison rules
----------------
Text and names (company, person, university, department, ...):
    NFKC, then every whitespace character removed. So "㈜테스트" == "(주)테스트" and
    "주식회사 가가" == "주식회사가가". Nothing else is normalised (no case folding,
    no legal-entity stripping, no fuzzy matching).
Numbers and dates stay strict:
    business_registration_number  its 10 digits
    student_id                    its digits
    dates                         ISO yyyy-mm-dd
    gpa                           number, 2 decimals
    gpa_scale                     number as 4.5 / 4.3

Field outcome (on the extractor's machine value, as in v1):
    CORRECT / WRONG (non-null, differs) / UNRESOLVED (null) /
    NOT_EVALUATED (manifest VERIFIED_ABSENT: CORRECT_ABSTENTION, or WRONG if a value is produced).

OCR field decision (new): only for documents without a text layer (scanned / images).
    AUTO_ACCEPTED   the system acts on the machine value without a human
                    (an effective value exists)
    NEEDS_HUMAN     no effective value: a human must confirm or supply it
    A decision is scored on the effective value the system acts on:
    FALSE AUTO-ACCEPT = AUTO_ACCEPTED and the effective value is WRONG.

Metrics (per version)
    auto-accept rate        AUTO_ACCEPTED / OCR evaluated fields
    false auto-accept       count (target 0)
    review burden           fields (KNOWN_VALUE or VERIFIED_ABSENT in the manifest) with no effective
                            value, per submission -- i.e. fields a human must still confirm/supply
    all-flagged burden      v1 definition: fields with needs_review, per submission
    auto-decided submission scanned/images submissions whose final status needs no human step
                            (READY or NEEDS_CORRECTION; REVIEW_REQUIRED does) -- and how many of
                            those equal the digital expectation
    false READY             submission READY where the (digital-counterpart) expectation is not READY,
                            or any effective field is WRONG. READY on a RECORD row is listed
                            separately (READY_ON_RECORD) unless a field is wrong.
    processing time

Status expectations
    digital:      manifest expected[digital].submission_status
    scanned/images: the digital expectation (the manifest's scanned expectations encode the old
                  always-review policy). REVIEW_REQUIRED where the digital expectation is READY or
                  NEEDS_CORRECTION is CONSERVATIVE (safe, not a match).
    "record actual" / " or " -> RECORD (not scored).
    Owner decision 3: an expectation whose issue-code list mentions an UNKNOWN classification
    (look-alike documents: B11, S07 and their hold-out analogues) expects REVIEW_REQUIRED.
    Owner decision 4: where the manifest expects a duplicate to be reported, the submission-level
    response must carry a duplicate notice (DUPLICATE_WARNING_VISIBLE).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_MANIFESTS = {
    "dev": REPO_ROOT / "evaluation" / "datasets" / "synthetic" / "test_variants" / "manifest.json",
    "holdout": REPO_ROOT / "evaluation" / "datasets" / "synthetic" / "holdout" / "manifest.json",
}
STATUS_TOKENS = ("READY", "REVIEW_REQUIRED", "NEEDS_CORRECTION", "FAILED")
DATE_FIELDS = {"issue_date", "valid_from", "valid_until"}
VERSIONS = ("digital", "scanned", "images")
OCR_VERSIONS = ("scanned", "images")


# --------------------------------------------------------------------------- compare


def text_key(value: Any) -> str:
    return "".join(unicodedata.normalize("NFKC", str(value)).split())


def normalize(field: str, value: Any) -> str | None:
    if value is None:
        return None
    if field in DATE_FIELDS:
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(value).strip())
        return match.group(0) if match else str(value).strip()
    if field == "business_registration_number" or field == "student_id":
        return "".join(ch for ch in str(value) if ch.isdigit())
    if field == "gpa":
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return text_key(value)
    if field == "gpa_scale":
        try:
            return f"{float(value):g}"
        except (TypeError, ValueError):
            return text_key(value)
    return text_key(value)


def score_field(field: str, spec: dict[str, Any], actual: dict[str, Any] | None, ocr_doc: bool) -> dict[str, Any]:
    state = spec.get("state")
    machine = None if actual is None else actual.get("machine_value", actual.get("value"))
    effective = None if actual is None else actual.get("value")
    produced = machine is not None and str(machine).strip() != ""
    acted = effective is not None and str(effective).strip() != ""
    auto = actual.get("auto_acceptance") if actual else None
    out: dict[str, Any] = {
        "state": state,
        "actual": machine,
        "effective": effective,
        "acts": acted,
        "needs_review_flag": bool(actual and actual.get("needs_review")),
        "auto_acceptance": auto,
    }
    if state == "VERIFIED_ABSENT":
        out["outcome"] = "WRONG" if produced else "CORRECT_ABSTENTION"
        out["category"] = "NOT_EVALUATED"
        out["effective_outcome"] = "WRONG" if acted else None
    elif state == "KNOWN_VALUE":
        expected = normalize(field, spec.get("value"))
        out["expected"] = expected
        out["category"] = "EVALUATED"
        if not produced:
            out["outcome"] = "UNRESOLVED"
        elif normalize(field, machine) == expected:
            out["outcome"] = "CORRECT"
        else:
            out["outcome"] = "WRONG"
        if acted:
            out["effective_outcome"] = "CORRECT" if normalize(field, effective) == expected else "WRONG"
        else:
            out["effective_outcome"] = None
    else:
        out["outcome"] = "RECORD"
        out["category"] = "RECORD"
        out["effective_outcome"] = None
    if ocr_doc and out["category"] in ("EVALUATED",):
        out["decision"] = "AUTO_ACCEPTED" if acted else "NEEDS_HUMAN"
        out["false_auto_accept"] = bool(acted and out["effective_outcome"] == "WRONG")
    elif ocr_doc and out["category"] == "NOT_EVALUATED":
        out["decision"] = "AUTO_ACCEPTED" if acted else "NEEDS_HUMAN"
        out["false_auto_accept"] = bool(acted)
    return out


def status_expectation(expected_block: dict[str, Any]) -> tuple[str, str | None]:
    """(kind, token): kind SCORED or RECORD."""
    text = expected_block.get("submission_status")
    codes = " ".join(str(code) for code in expected_block.get("issue_codes", []))
    if not text:
        return "RECORD", None
    lowered = text.lower()
    if "record actual" in lowered or re.search(r"\bor\b", lowered):
        return "RECORD", None
    for token in STATUS_TOKENS:
        if text.strip().startswith(token):
            if token == "NEEDS_CORRECTION" and "UNKNOWN" in codes.upper():
                return "SCORED", "REVIEW_REQUIRED"  # owner decision 3
            return "SCORED", token
    return "RECORD", None


def expects_duplicate_notice(expected_block: dict[str, Any]) -> bool:
    return any("duplicate" in str(code).lower() for code in expected_block.get("issue_codes", []))


def burden(files: list[dict[str, Any]], by_file: dict[str, Any]) -> dict[str, int]:
    needs = flagged = 0
    for record in files:
        manifest_entry = by_file.get(record["file"]) or {}
        fields = record.get("fields") or {}
        for name, spec in (manifest_entry.get("expected_fields") or {}).items():
            if spec.get("state") not in ("KNOWN_VALUE", "VERIFIED_ABSENT"):
                continue
            info = fields.get(name)
            if info is None or info.get("value") is None:
                needs += 1
        flagged += sum(1 for info in fields.values() if info.get("needs_review"))
    return {"needs_human": needs, "all_flagged": flagged}


def score_file(record: dict[str, Any], entry: dict[str, Any] | None) -> dict[str, Any]:
    expected = (entry or {}).get("expected_classification")
    processed = record.get("upload_status") == 201 and record.get("process_status_code") == 200
    ocr_doc = bool(entry) and not entry.get("text_layer", True)
    out: dict[str, Any] = {
        "file": record["file"],
        "expected": expected,
        "predicted": record.get("predicted_document_type"),
        "document_status": record.get("overall_status"),
        "upload_status": record.get("upload_status"),
        "process_status_code": record.get("process_status_code"),
        "processing_status": record.get("processing_status"),
        "process_ms": record.get("process_ms"),
        "issues": record.get("issues"),
        "classification_meta": record.get("classification_meta"),
        "processed": processed,
        "ocr_doc": ocr_doc,
    }
    if expected in (None, "n/a"):
        out["classification"] = "NOT_SCORED"
    elif not processed:
        out["classification"] = "NOT_PROCESSED"
    else:
        out["classification"] = "MATCH" if out["predicted"] == expected else "MISMATCH"
    out["fields"] = {}
    if processed and expected not in (None, "n/a", "UNKNOWN"):
        fields = record.get("fields") or {}
        for name, spec in ((entry or {}).get("expected_fields") or {}).items():
            out["fields"][name] = score_field(name, spec, fields.get(name), ocr_doc)
    return out


def score(raw: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    by_file = {item["file"]: item for item in manifest["files"]}
    scenarios = {s["set_id"]: s for s in manifest["business_sets"] + manifest["student_sets"]}
    scored: dict[str, Any] = {"sets": {}, "format_sets": {}}
    for set_id, set_result in raw.get("sets", {}).items():
        scenario = scenarios[set_id]
        digital_kind, digital_token = status_expectation(scenario["expected"].get("digital", {}))
        out_set: dict[str, Any] = {"title": set_result.get("title"), "versions": {}}
        for version, vres in set_result["versions"].items():
            base = "digital" if version == "digital_partial_checklist" else version
            expected_block = scenario["expected"].get(base, {})
            if base in OCR_VERSIONS:
                kind, token = digital_kind, digital_token
                expected_text = f"(digital expectation) {scenario['expected'].get('digital', {}).get('submission_status')}"
            else:
                kind, token = status_expectation(expected_block)
                expected_text = expected_block.get("submission_status")
            actual = vres.get("actual_submission_status")
            files = [score_file(r, by_file.get(r["file"])) for r in vres.get("files", [])]
            trusted_wrong = [
                f"{f['file'].rsplit('/', 1)[-1]}:{name}"
                for f in files
                for name, fs in f["fields"].items()
                if fs.get("effective_outcome") == "WRONG"
            ]
            if kind == "RECORD":
                comparison = "RECORD"
            elif actual == token:
                comparison = "MATCH"
            elif base in OCR_VERSIONS and actual == "REVIEW_REQUIRED":
                comparison = "CONSERVATIVE"
            else:
                comparison = "MISMATCH"
            false_ready = actual == "READY" and (
                (kind == "SCORED" and token != "READY") or bool(trusted_wrong)
            )
            ready_on_record = actual == "READY" and kind == "RECORD" and not false_ready
            notices = vres.get("notices") or []
            dup_visible = any("DUPLICATE" in str(n.get("code", "")).upper() for n in notices) or any(
                "DUPLICATE" in str(code).upper() for code in (vres.get("actual_issue_codes") or [])
            )
            out_set["versions"][version] = {
                "expected_status": expected_text,
                "actual_status": actual,
                "status_comparison": comparison,
                "false_ready": false_ready,
                "ready_on_record": ready_on_record,
                "trusted_wrong_fields": trusted_wrong,
                "auto_decided": base in OCR_VERSIONS and actual in ("READY", "NEEDS_CORRECTION"),
                "duplicate_notice_expected": expects_duplicate_notice(scenario["expected"].get("digital", {})),
                "duplicate_notice_visible": dup_visible,
                "issue_codes": vres.get("actual_issue_codes"),
                "elapsed_seconds": vres.get("elapsed_seconds"),
                "burden": burden(vres.get("files", []), by_file),
                "files": files,
            }
        scored["sets"][set_id] = out_set
    for set_id, fres in raw.get("format_sets", {}).items():
        scored["format_sets"][set_id] = {
            "title": fres.get("title"),
            "expected": fres.get("expected"),
            "elapsed_seconds": fres.get("elapsed_seconds"),
            "files": [score_file(r, by_file.get(r["file"])) for r in fres.get("files", [])],
        }
    return scored


# --------------------------------------------------------------------------- aggregation


def aggregate(scored: dict[str, Any]) -> dict[str, Any]:
    cls: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    fields: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_version: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    burden_needs: dict[str, list[int]] = defaultdict(list)
    burden_flagged: dict[str, list[int]] = defaultdict(list)
    times: dict[str, list[float]] = defaultdict(list)
    false_ready: list[str] = []
    ready_on_record: list[str] = []
    auto_decided: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    status: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    duplicates: list[str] = []
    trusted_wrong: list[str] = []
    for set_id, sset in scored["sets"].items():
        for version, v in sset["versions"].items():
            tag = f"{set_id}/{version}"
            if v["false_ready"]:
                false_ready.append(tag)
            if version == "digital_partial_checklist":
                continue
            if v["ready_on_record"]:
                ready_on_record.append(tag)
            if v["duplicate_notice_expected"] and version == "digital":
                duplicates.append(f"{set_id}: visible={v['duplicate_notice_visible']}")
            status[version][v["status_comparison"]] += 1
            burden_needs[version].append(v["burden"]["needs_human"])
            burden_flagged[version].append(v["burden"]["all_flagged"])
            trusted_wrong.extend(f"{tag}:{item}" for item in v["trusted_wrong_fields"])
            if version in OCR_VERSIONS:
                auto_decided[version]["submissions"] += 1
                if v["auto_decided"]:
                    auto_decided[version]["auto_decided"] += 1
                    if v["status_comparison"] == "MATCH":
                        auto_decided[version]["auto_decided_correct"] += 1
            for f in v["files"]:
                if f.get("process_ms") is not None:
                    times[version].append(f["process_ms"])
                expected = f["expected"]
                if f["classification"] in ("MATCH", "MISMATCH", "NOT_PROCESSED"):
                    cls[f"{expected}|{version}"]["total"] += 1
                    cls[f"{expected}|{version}"][f["classification"]] += 1
                for name, fs in f["fields"].items():
                    if fs["category"] == "RECORD":
                        continue
                    key = f"{expected}|{version}"
                    if fs["category"] == "NOT_EVALUATED":
                        fields[key]["NE_" + fs["outcome"]] += 1
                        per_version[version]["NE_" + fs["outcome"]] += 1
                    else:
                        fields[key][fs["outcome"]] += 1
                        fields[key]["evaluated"] += 1
                        per_version[version][fs["outcome"]] += 1
                        per_version[version]["evaluated"] += 1
                        if fs["acts"]:
                            per_version[version]["acts"] += 1
                            if fs["effective_outcome"] == "CORRECT":
                                per_version[version]["acts_correct"] += 1
                    if fs.get("decision") == "AUTO_ACCEPTED":
                        per_version[version]["auto_accepted"] += 1
                    if fs.get("false_auto_accept"):
                        per_version[version]["false_auto_accept"] += 1
                    if f["ocr_doc"] and fs["category"] == "EVALUATED":
                        per_version[version]["ocr_evaluated"] += 1
    return {
        "classification": {k: dict(v) for k, v in cls.items()},
        "fields": {k: dict(v) for k, v in fields.items()},
        "per_version": {k: dict(v) for k, v in per_version.items()},
        "status_comparison": {k: dict(v) for k, v in status.items()},
        "burden_needs_human_mean": {v: round(statistics.mean(x), 2) for v, x in burden_needs.items() if x},
        "burden_needs_human_total": {v: sum(x) for v, x in burden_needs.items()},
        "burden_all_flagged_mean": {v: round(statistics.mean(x), 2) for v, x in burden_flagged.items() if x},
        "auto_decided": {k: dict(v) for k, v in auto_decided.items()},
        "process_ms_mean": {v: round(statistics.mean(x), 1) for v, x in times.items() if x},
        "process_ms_max": {v: round(max(x), 1) for v, x in times.items() if x},
        "false_ready": false_ready,
        "ready_on_record": ready_on_record,
        "duplicate_notice": duplicates,
        "trusted_wrong_fields": trusted_wrong,
    }


def f16_outcome(files: list[dict[str, Any]]) -> list[tuple[str, str]]:
    rows = []
    for f in files:
        if f["upload_status"] != 201:
            outcome, ok = f"REJECTED_AT_UPLOAD ({f['upload_status']})", True
        elif f["process_status_code"] != 200:
            outcome = f"PROCESS_HTTP_{f['process_status_code']}"
            ok = f["process_status_code"] is not None and f["process_status_code"] < 500
        elif f["processing_status"] == "FAILED":
            outcome, ok = "FAILED", True
        else:
            outcome = f"PROCESSED ({f['processing_status']}, doc={f['document_status']})"
            ok = f["document_status"] != "READY"
        rows.append((f["file"].rsplit("/", 1)[-1], outcome + (" OK" if ok else " UNSAFE")))
    return rows


def pct(num: int, den: int) -> str:
    return f"{100 * num / den:.1f}%" if den else "-"


def render_report(label: str, scored: dict[str, Any], agg: dict[str, Any], meta: dict[str, Any], detail: bool = True) -> str:
    L: list[str] = []
    w = L.append
    w(f"# {label} report (scorer v2)\n")
    w(f"- Scorer v2 SHA-256 `{meta['scorer_sha256']}`; manifest SHA-256 `{meta['manifest_sha256']}`")
    w(f"- Corpus `{meta['corpus']}`, git `{meta.get('git_head', '?')}`, strategy `{meta.get('strategy')}`, project values `{meta.get('project_values')}`\n")
    w("## 1. Submission status per set × version\n")
    w("| Set | Version | Expected | Actual | Result | Notes |")
    w("|---|---|---|---|---|---|")
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for set_id, sset in scored["sets"].items():
        for version, v in sset["versions"].items():
            base = "digital" if version == "digital_partial_checklist" else version
            counts[base][v["status_comparison"]] += 1
            note = []
            if v["false_ready"]:
                note.append("FALSE-READY")
            if v["trusted_wrong_fields"]:
                note.append("trusted-wrong " + ",".join(v["trusted_wrong_fields"]))
            if v["duplicate_notice_expected"] and version == "digital":
                note.append(f"duplicate notice visible={v['duplicate_notice_visible']}")
            codes = ", ".join(sorted(set(v["issue_codes"] or [])))
            w(f"| {set_id} | {version} | {v['expected_status']} | {v['actual_status']} | {v['status_comparison']} | {'; '.join(note)} {codes} |")
    w("\nStatus totals: " + json.dumps({k: dict(v) for k, v in counts.items()}))
    w("\n## 2. Classification\n")
    w("| Type | Version | Match / total | Mismatch |")
    w("|---|---|---|---|")
    for key in sorted(agg["classification"]):
        t, v = key.split("|")
        c = agg["classification"][key]
        w(f"| {t} | {v} | {c.get('MATCH', 0)}/{c['total']} | {c.get('MISMATCH', 0)} |")
    w("\n## 3. Field outcomes (machine value) and OCR auto-acceptance\n")
    w("| Version | CORRECT | WRONG | UNRESOLVED | of N | acts (effective value) | acts correct | AUTO_ACCEPTED | false auto-accept | auto-accept rate |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for v in VERSIONS:
        c = agg["per_version"].get(v, {})
        w(
            f"| {v} | {c.get('CORRECT', 0)} | {c.get('WRONG', 0)} | {c.get('UNRESOLVED', 0)} | {c.get('evaluated', 0)} | "
            f"{c.get('acts', 0)} | {c.get('acts_correct', 0)} | {c.get('auto_accepted', 0)} | {c.get('false_auto_accept', 0)} | "
            f"{pct(c.get('auto_accepted', 0), c.get('ocr_evaluated', 0)) if v in OCR_VERSIONS else 'n/a'} |"
        )
    w("\nAbsent-field checks (VERIFIED_ABSENT): " + json.dumps({v: {k: n for k, n in agg['per_version'].get(v, {}).items() if k.startswith('NE_')} for v in VERSIONS}))
    w("\n| Type | Version | CORRECT | WRONG | UNRESOLVED | of N |")
    w("|---|---|---|---|---|---|")
    for key in sorted(agg["fields"]):
        t, v = key.split("|")
        c = agg["fields"][key]
        w(f"| {t} | {v} | {c.get('CORRECT', 0)} | {c.get('WRONG', 0)} | {c.get('UNRESOLVED', 0)} | {c.get('evaluated', 0)} |")
    w("\n## 4. Safety\n")
    w(f"- False READY: **{len(agg['false_ready'])}** {agg['false_ready']}")
    w(f"- Effective (acted-on) values that are WRONG: {agg['trusted_wrong_fields']}")
    w(f"- READY on RECORD rows (digital): {agg['ready_on_record']}")
    w(f"- Duplicate-notice expectation: {agg['duplicate_notice']}\n")
    w("## 5. Review burden and automatic decisions\n")
    w("| Version | needs-human fields / submission (mean) | total | all-flagged / submission (v1 style) | auto-decided submissions | of which equal to digital expectation |")
    w("|---|---|---|---|---|---|")
    for v in VERSIONS:
        ad = agg["auto_decided"].get(v, {})
        w(
            f"| {v} | {agg['burden_needs_human_mean'].get(v, '-')} | {agg['burden_needs_human_total'].get(v, '-')} | "
            f"{agg['burden_all_flagged_mean'].get(v, '-')} | "
            f"{ad.get('auto_decided', 0)}/{ad.get('submissions', 0)} | {ad.get('auto_decided_correct', 0)} |"
        )
    w("\n## 6. Processing time per document (ms)\n")
    w("| Version | Mean | Max |")
    w("|---|---|---|")
    for v in VERSIONS:
        w(f"| {v} | {agg['process_ms_mean'].get(v, '-')} | {agg['process_ms_max'].get(v, '-')} |")
    w("\n## 7. Format sets\n")
    w("| Set | Title | Files | Classification MATCH/scored | Processed | Document statuses |")
    w("|---|---|---|---|---|---|")
    for set_id, fs in scored["format_sets"].items():
        files = fs["files"]
        scored_files = [f for f in files if f["classification"] in ("MATCH", "MISMATCH", "NOT_PROCESSED")]
        statuses: dict[str, int] = defaultdict(int)
        for f in files:
            statuses[str(f["document_status"])] += 1
        flagged = sum(1 for f in files if (f.get("classification_meta") or {}).get("multiple_documents_in_file"))
        w(
            f"| {set_id} | {fs['title']} | {len(files)} | {sum(1 for f in files if f['classification'] == 'MATCH')}/{len(scored_files)} | "
            f"{sum(1 for f in files if f['processed'])} | {dict(statuses)} multi-doc-flagged={flagged} |"
        )
    corrupt = next((fs for key, fs in scored["format_sets"].items() if "corrupt" in str(fs.get("title", "")).lower() or "Truncated" in str(fs.get("title", ""))), None)
    if corrupt:
        w("\n### Corrupt files\n")
        w("| File | Outcome |")
        w("|---|---|")
        for name, outcome in f16_outcome(corrupt["files"]):
            w(f"| {name} | {outcome} |")
    return "\n".join(L) + "\n"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--corpus", choices=["dev", "holdout"], default="dev")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--label", default="B0")
    args = parser.parse_args()
    if args.corpus == "holdout" and os.environ.get("ADVS_FINAL_JUDGEMENT") != "1":
        raise SystemExit("Refusing to score the hold-out set outside final judgement.")
    manifest_path = CORPUS_MANIFESTS[args.corpus]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    scored = score(raw, manifest)
    agg = aggregate(scored)
    meta = {
        "scorer_sha256": sha256_of(Path(__file__)),
        "manifest_sha256": sha256_of(manifest_path),
        "corpus": args.corpus,
        "git_head": raw.get("git_head"),
        "strategy": raw.get("strategy"),
        "project_values": raw.get("project_values"),
    }
    args.out_json.write_text(json.dumps({"meta": meta, "aggregate": agg, "scored": scored, "raw": raw}, ensure_ascii=False, indent=1), encoding="utf-8")
    args.out_md.write_text(render_report(args.label, scored, agg, meta), encoding="utf-8")
    print(f"scorer v2 sha256 {meta['scorer_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
