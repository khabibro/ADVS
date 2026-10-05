"""Frozen scorer for the ADVS test-variant corpus.

Reads the raw harness output (run_variants.py) plus the answer key
(evaluation/datasets/synthetic/test_variants/manifest.json) and produces a
scored JSON and a Markdown report. This file is frozen at Phase C step B0;
its SHA-256 is recorded in the B0 report and re-checked at B1.

Comparison rules (also printed in every report)
-----------------------------------------------
Classification
    predicted document type == manifest `expected_classification`.
    Files whose expectation is "n/a" (corrupt-file set F16) are not scored.

Fields (only for KNOWN_VALUE / VERIFIED_ABSENT manifest entries of files whose
expected_classification is a supported type; fields of expected-UNKNOWN files
are not scored)
    System value is the field's effective normalized value. Normalization
    before comparing, by field:
      * dates (issue_date, valid_from, valid_until)  -> ISO yyyy-mm-dd string
      * business_registration_number                 -> its 10 digits
      * gpa                                          -> number, 2 decimals
      * gpa_scale                                    -> number as 4.5 / 4.3
      * everything else (names, text)                -> whitespace collapsed
        ONLY (no case folding, no punctuation or legal-entity stripping)
    Outcome:
      CORRECT     equal
      WRONG       non-null value that differs (the dangerous case)
      UNRESOLVED  null / abstained
      NOT_EVALUATED  manifest state VERIFIED_ABSENT, counted separately:
                  CORRECT_ABSTENTION if the system produced no value,
                  WRONG if it produced one.
    Values are scored on the extractor's own machine value (`normalized_value`),
    so OCR extraction quality is visible even though OCR fields are always
    gated to human review. A field is "flagged" when the system will not act
    on it without a human (no effective value, or needs_review). WRONG is split
    by that: an UNFLAGGED wrong value (the system would act on it) is the
    dangerous case. The harness also records the effective (policy-gated) value;
    the report adds "trusted correct" = CORRECT and unflagged.

Submission status
    actual vs expected[version].submission_status. An expected string that
    contains "record actual" or the word "or" is RECORD (reported, not
    scored). Otherwise the leading status token must equal the actual status.
    B07 `digital_partial_checklist` is scored against B07's digital
    expectation.

False READY
    The submission returned READY where the expected status is not READY, or
    where the version is scanned/images (OCR policy: never READY without human
    confirmation). READY on a RECORD row of a digital version is listed
    separately as READY_ON_RECORD for manual judgement.

Review burden
    Number of extracted fields with needs_review=True per submission, split
    into fields with a value (confirm) and fields without one (supply).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "evaluation" / "datasets" / "synthetic" / "test_variants" / "manifest.json"
STATUS_TOKENS = ("READY", "REVIEW_REQUIRED", "NEEDS_CORRECTION", "FAILED")
DATE_FIELDS = {"issue_date", "valid_from", "valid_until"}
VERSIONS = ("digital", "scanned", "images")

# Expectations the scorer applies literally but whose reading is disputed. The
# outcome is NOT altered (the manifest is the target); disputed WRONG results
# are only annotated and counted separately so the user can decide.
#   key: (file basename, field)  -> reason
DISPUTED_EXPECTATIONS: dict[tuple[str, str], str] = {
    (
        "B02-3_납세증명서.pdf",
        "company_name",
    ): (
        "manifest value uses the compatibility character U+3231 (㈜); the system folds it to the "
        "canonical '(주)' by Unicode NFKC at extraction. Same text, different code points."
    ),
}


def disputed_reason(file: str, field: str) -> str | None:
    base = file.rsplit("/", 1)[-1]
    for (prefix, name), reason in DISPUTED_EXPECTATIONS.items():
        if name == field and base == prefix:
            return reason
    return None


def collapse_ws(value: Any) -> str:
    return " ".join(str(value).split())


def normalize(field: str, value: Any) -> str | None:
    if value is None:
        return None
    if field in DATE_FIELDS:
        text = str(value).strip()
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
        return match.group(0) if match else text
    if field == "business_registration_number":
        return "".join(ch for ch in str(value) if ch.isdigit())
    if field == "gpa":
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return collapse_ws(value)
    if field == "gpa_scale":
        try:
            return f"{float(value):g}"
        except (TypeError, ValueError):
            return collapse_ws(value)
    return collapse_ws(value)


def score_field(field: str, spec: dict[str, Any], actual: dict[str, Any] | None) -> dict[str, Any]:
    state = spec.get("state")
    # Scored on the extractor's own (machine) value, so OCR extraction quality
    # is visible. `flagged` = the system would NOT act on it without a human:
    # no effective (policy-trusted) value, or needs_review set.
    value = None if actual is None else actual.get("machine_value", actual.get("value"))
    flagged = actual is None or actual.get("value") is None or bool(actual.get("needs_review"))
    produced = value is not None and str(value).strip() != ""
    if state == "VERIFIED_ABSENT":
        outcome = "WRONG" if produced else "CORRECT_ABSTENTION"
        return {"state": state, "outcome": outcome, "actual": value, "flagged": flagged, "category": "NOT_EVALUATED"}
    if state != "KNOWN_VALUE":
        return {"state": state, "outcome": "RECORD", "actual": value, "flagged": flagged, "category": "RECORD"}
    expected = normalize(field, spec.get("value"))
    if not produced:
        outcome = "UNRESOLVED"
    elif normalize(field, value) == expected:
        outcome = "CORRECT"
    else:
        outcome = "WRONG"
    return {
        "state": state,
        "outcome": outcome,
        "expected": expected,
        "actual": value,
        "flagged": flagged,
        "category": "EVALUATED",
    }


def classify_status(expected: str | None) -> tuple[str, str | None]:
    """-> (kind, token); kind is SCORED or RECORD."""
    if not expected:
        return "RECORD", None
    lowered = expected.lower()
    if "record actual" in lowered or re.search(r"\bor\b", lowered):
        return "RECORD", None
    for token in STATUS_TOKENS:
        if expected.strip().startswith(token):
            return "SCORED", token
    return "RECORD", None


def review_burden(files: list[dict[str, Any]]) -> dict[str, int]:
    confirm = supply = 0
    for record in files:
        for info in (record.get("fields") or {}).values():
            if info.get("needs_review"):
                if info.get("value") is None:
                    supply += 1
                else:
                    confirm += 1
    return {"total": confirm + supply, "confirm_value": confirm, "supply_value": supply}


def score_file(record: dict[str, Any], manifest_entry: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "file": record["file"],
        "predicted": record.get("predicted_document_type"),
        "needs_review_classification": record.get("classification_needs_review"),
        "document_status": record.get("overall_status"),
        "upload_status": record.get("upload_status"),
        "process_status_code": record.get("process_status_code"),
        "processing_status": record.get("processing_status"),
        "processing_error_code": record.get("processing_error_code"),
        "process_ms": record.get("process_ms"),
        "issues": record.get("issues"),
    }
    expected = (manifest_entry or {}).get("expected_classification")
    out["expected"] = expected
    processed = record.get("upload_status") == 201 and record.get("process_status_code") == 200
    out["processed"] = processed
    if expected in (None, "n/a"):
        out["classification"] = "NOT_SCORED"
    elif not processed:
        out["classification"] = "NOT_PROCESSED"
    else:
        out["classification"] = "MATCH" if out["predicted"] == expected else "MISMATCH"
    out["fields"] = {}
    if processed and expected not in (None, "n/a", "UNKNOWN"):
        fields = record.get("fields") or {}
        for name, spec in ((manifest_entry or {}).get("expected_fields") or {}).items():
            scored_field = score_field(name, spec, fields.get(name))
            reason = disputed_reason(record["file"], name)
            if reason:
                scored_field["EXPECTATION_DISPUTED"] = reason
            out["fields"][name] = scored_field
    return out


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(raw: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    by_file = {entry["file"]: entry for entry in manifest["files"]}
    scenarios = {s["set_id"]: s for s in manifest["business_sets"] + manifest["student_sets"]}
    scored: dict[str, Any] = {"sets": {}, "format_sets": {}}

    for set_id, set_result in raw.get("sets", {}).items():
        scenario = scenarios[set_id]
        scored_set: dict[str, Any] = {"title": set_result.get("title"), "versions": {}}
        for version, vres in set_result["versions"].items():
            expect_key = "digital" if version == "digital_partial_checklist" else version
            expected_block = scenario["expected"].get(expect_key, {})
            expected_text = expected_block.get("submission_status")
            kind, token = classify_status(expected_text)
            actual = vres.get("actual_submission_status")
            if kind == "RECORD":
                comparison = "RECORD"
            else:
                comparison = "MATCH" if actual == token else "MISMATCH"
            ocr_version = expect_key in ("scanned", "images")
            if actual == "READY" and ocr_version:
                false_ready = True
            elif actual == "READY" and kind == "SCORED" and token != "READY":
                false_ready = True
            else:
                false_ready = False
            ready_on_record = actual == "READY" and kind == "RECORD" and not ocr_version
            files = [score_file(r, by_file.get(r["file"])) for r in vres.get("files", [])]
            scored_set["versions"][version] = {
                "expected_status": expected_text,
                "actual_status": actual,
                "status_comparison": comparison,
                "false_ready": false_ready,
                "ready_on_record": ready_on_record,
                "issue_codes": vres.get("actual_issue_codes"),
                "elapsed_seconds": vres.get("elapsed_seconds"),
                "review_burden": review_burden(vres.get("files", [])),
                "files": files,
            }
        scored["sets"][set_id] = scored_set

    for set_id, fres in raw.get("format_sets", {}).items():
        files = [score_file(r, by_file.get(r["file"])) for r in fres.get("files", [])]
        scored["format_sets"][set_id] = {
            "title": fres.get("title"),
            "expected": fres.get("expected"),
            "elapsed_seconds": fres.get("elapsed_seconds"),
            "files": files,
        }
    return scored


# --------------------------------------------------------------------------
# aggregation + report
# --------------------------------------------------------------------------


def aggregate(scored: dict[str, Any]) -> dict[str, Any]:
    cls: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    fields: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    wrong_unflagged: dict[str, int] = defaultdict(int)
    wrong_disputed: dict[str, int] = defaultdict(int)
    burden: dict[str, list[int]] = defaultdict(list)
    times: dict[str, list[float]] = defaultdict(list)
    false_ready: list[str] = []
    ready_on_record: list[str] = []
    for set_id, sset in scored["sets"].items():
        for version, v in sset["versions"].items():
            if version == "digital_partial_checklist":
                if v["false_ready"]:
                    false_ready.append(f"{set_id}/{version}")
                continue
            if v["false_ready"]:
                false_ready.append(f"{set_id}/{version}")
            if v["ready_on_record"]:
                ready_on_record.append(f"{set_id}/{version}")
            burden[version].append(v["review_burden"]["total"])
            for f in v["files"]:
                if f.get("process_ms") is not None:
                    times[version].append(f["process_ms"])
                expected = f["expected"]
                if f["classification"] in ("MATCH", "MISMATCH", "NOT_PROCESSED"):
                    cls[(expected, version)]["total"] += 1
                    cls[(expected, version)][f["classification"]] += 1
                for name, fs in f["fields"].items():
                    if fs["category"] == "RECORD":
                        continue
                    key = (expected, version)
                    if fs["category"] == "NOT_EVALUATED":
                        fields[key]["NE_" + fs["outcome"]] += 1
                    else:
                        fields[key][fs["outcome"]] += 1
                        fields[key]["evaluated"] += 1
                        if fs["outcome"] == "CORRECT" and not fs["flagged"]:
                            fields[key]["TRUSTED_CORRECT"] += 1
                    if fs["outcome"] == "WRONG" and not fs["flagged"]:
                        wrong_unflagged[version] += 1
                    if fs["outcome"] == "WRONG" and fs.get("EXPECTATION_DISPUTED"):
                        wrong_disputed[version] += 1
    return {
        "classification": {f"{k[0]}|{k[1]}": dict(v) for k, v in cls.items()},
        "fields": {f"{k[0]}|{k[1]}": dict(v) for k, v in fields.items()},
        "wrong_unflagged": dict(wrong_unflagged),
        "wrong_disputed": dict(wrong_disputed),
        "review_burden_mean": {v: round(statistics.mean(x), 1) for v, x in burden.items() if x},
        "review_burden_total": {v: sum(x) for v, x in burden.items()},
        "process_ms_mean": {v: round(statistics.mean(x), 1) for v, x in times.items() if x},
        "process_ms_max": {v: round(max(x), 1) for v, x in times.items() if x},
        "false_ready": false_ready,
        "ready_on_record": ready_on_record,
    }


def f16_outcome(files: list[dict[str, Any]]) -> list[tuple[str, str]]:
    rows = []
    for f in files:
        if f["upload_status"] != 201:
            outcome = f"REJECTED_AT_UPLOAD ({f['upload_status']})"
            ok = True
        elif f["process_status_code"] != 200:
            outcome = f"PROCESS_HTTP_{f['process_status_code']}"
            ok = f["process_status_code"] is not None and f["process_status_code"] < 500
        elif f["processing_status"] == "FAILED":
            outcome = "FAILED"
            ok = True
        else:
            outcome = f"PROCESSED ({f['processing_status']}, doc={f['document_status']})"
            ok = f["document_status"] != "READY"
        rows.append((f["file"].split("/")[-1], outcome + (" OK" if ok else " UNSAFE")))
    return rows


def render_report(label: str, scored: dict[str, Any], agg: dict[str, Any], meta: dict[str, str]) -> str:
    L: list[str] = []
    w = L.append
    w(f"# {label} report — ADVS test-variant corpus\n")
    w(f"- Scorer: `evaluation/harness/score_variants.py` SHA-256 `{meta['scorer_sha256']}`")
    w(f"- Harness: `evaluation/harness/run_variants.py` SHA-256 `{meta['harness_sha256']}`")
    w(f"- Manifest SHA-256 `{meta['manifest_sha256']}`")
    w(f"- Git HEAD at run: `{meta.get('git_head', '?')}`; submission date fixed to the manifest value.\n")
    w("## Scoring rules\n")
    w("```")
    w((__doc__ or "").split("Comparison rules (also printed in every report)")[-1].split("\"\"\"")[0].strip())
    w("```\n")

    w("## 1. Submission status per set × version\n")
    w("| Set | Version | Expected | Actual | Result | Issue codes |")
    w("|---|---|---|---|---|---|")
    counts: dict[str, int] = defaultdict(int)
    for set_id, sset in scored["sets"].items():
        for version, v in sset["versions"].items():
            counts[v["status_comparison"]] += 1
            codes = sorted(set(v["issue_codes"] or []))
            w(
                f"| {set_id} | {version} | {v['expected_status']} | {v['actual_status']} | "
                f"{v['status_comparison']}{' ⚠FALSE-READY' if v['false_ready'] else ''} | {', '.join(codes)} |"
            )
    w(f"\nTotals: {dict(counts)}\n")

    w("## 2. Classification accuracy per document type × version\n")
    w("| Type | Version | Match / total | Mismatch | Not processed |")
    w("|---|---|---|---|---|")
    for key in sorted(agg["classification"]):
        t, v = key.split("|")
        c = agg["classification"][key]
        w(f"| {t} | {v} | {c.get('MATCH', 0)}/{c['total']} | {c.get('MISMATCH', 0)} | {c.get('NOT_PROCESSED', 0)} |")

    w("\n## 3. Field outcomes per document type × version\n")
    w("Denominator = evaluated KNOWN_VALUE fields. NOT_EVALUATED (VERIFIED_ABSENT) counted separately.\n")
    w("| Type | Version | CORRECT | WRONG | UNRESOLVED | of N | Absent: correct abstention / WRONG |")
    w("|---|---|---|---|---|---|---|")
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for key in sorted(agg["fields"]):
        t, v = key.split("|")
        c = agg["fields"][key]
        for k, n in c.items():
            totals[v][k] += n
        w(
            f"| {t} | {v} | {c.get('CORRECT', 0)} | {c.get('WRONG', 0)} | {c.get('UNRESOLVED', 0)} | "
            f"{c.get('evaluated', 0)} | {c.get('NE_CORRECT_ABSTENTION', 0)} / {c.get('NE_WRONG', 0)} |"
        )
    w("\n| Version | CORRECT | WRONG | UNRESOLVED | of N | WRONG unflagged | CORRECT and trusted (no review needed) | Absent: abstained / WRONG |")
    w("|---|---|---|---|---|---|---|---|")
    for v in VERSIONS:
        c = totals.get(v, {})
        w(
            f"| {v} | {c.get('CORRECT', 0)} | {c.get('WRONG', 0)} | {c.get('UNRESOLVED', 0)} | {c.get('evaluated', 0)} | "
            f"{agg['wrong_unflagged'].get(v, 0)} | {c.get('TRUSTED_CORRECT', 0)} | {c.get('NE_CORRECT_ABSTENTION', 0)} / {c.get('NE_WRONG', 0)} |"
        )

    w(f"\nWRONG results on an EXPECTATION_DISPUTED field (counted in WRONG above): {agg['wrong_disputed']}")
    for _set_id, _sset in scored["sets"].items():
        for _version, _v in _sset["versions"].items():
            for _f in _v["files"]:
                for _name, _fs in _f["fields"].items():
                    if _fs.get("EXPECTATION_DISPUTED"):
                        w(f"- {_f['file'].rsplit('/', 1)[-1]} / {_name}: {_fs['outcome']} ({_fs.get('actual')!r}) — {_fs['EXPECTATION_DISPUTED']}")

    w("\n## 4. False READY\n")
    w(f"- False READY count: **{len(agg['false_ready'])}** {agg['false_ready']}")
    w(f"- READY on RECORD rows (digital, manual judgement): {agg['ready_on_record']}\n")

    w("## 5. Review burden (fields needing human confirmation per submission)\n")
    w("| Version | Mean per submission | Total |")
    w("|---|---|---|")
    for v in VERSIONS:
        w(f"| {v} | {agg['review_burden_mean'].get(v, '-')} | {agg['review_burden_total'].get(v, '-')} |")

    w("\n## 6. Processing time per document (ms)\n")
    w("| Version | Mean | Max |")
    w("|---|---|---|")
    for v in VERSIONS:
        w(f"| {v} | {agg['process_ms_mean'].get(v, '-')} | {agg['process_ms_max'].get(v, '-')} |")

    w("\n## 7. Format sets\n")
    w("| Set | Title | Files | Classification MATCH/scored | Processed | Doc statuses | Notes |")
    w("|---|---|---|---|---|---|---|")
    for set_id, fs in scored["format_sets"].items():
        files = fs["files"]
        scored_files = [f for f in files if f["classification"] in ("MATCH", "MISMATCH", "NOT_PROCESSED")]
        match = sum(1 for f in files if f["classification"] == "MATCH")
        processed = sum(1 for f in files if f["processed"])
        statuses: dict[str, int] = defaultdict(int)
        for f in files:
            statuses[str(f["document_status"])] += 1
        rejected = sum(1 for f in files if f["upload_status"] != 201)
        w(
            f"| {set_id} | {fs['title']} | {len(files)} | {match}/{len(scored_files)} | {processed} | "
            f"{dict(statuses)} | uploads rejected: {rejected} |"
        )
    if "F16" in scored["format_sets"]:
        w("\n### F16 corrupt files\n")
        w("| File | Outcome |")
        w("|---|---|")
        for name, outcome in f16_outcome(scored["format_sets"]["F16"]["files"]):
            w(f"| {name} | {outcome} |")
    return "\n".join(L) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--label", default="B0")
    parser.add_argument("--git-head", default="")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    scored = score(raw, manifest)
    agg = aggregate(scored)
    meta = {
        "scorer_sha256": sha256_of(Path(__file__)),
        "harness_sha256": sha256_of(Path(__file__).with_name("run_variants.py")),
        "manifest_sha256": sha256_of(MANIFEST_PATH),
        "git_head": args.git_head,
    }
    args.out_json.write_text(
        json.dumps({"meta": meta, "aggregate": agg, "scored": scored, "raw": raw}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    args.out_md.write_text(render_report(args.label, scored, agg, meta), encoding="utf-8")
    print(f"scorer sha256 {meta['scorer_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
