"""Build manifest_v3.json next to each corpus manifest (the v2 manifest.json files are never edited).

v3 change log (also written into every manifest_v3.json as `v3_changelog` and into V3_CHANGELOG.md):
  1. S09 (all corpora), digital: REVIEW_REQUIRED + MISSING_REQUIRED_FIELD (student_id) -> READY.
     Reason: the student-number requirement was corrected after the real-document finding. A 재학증명서 that prints
     no 학번 is satisfied by a 성적증명서 that does; the documents are compared only when both print it.
  2. Dev set only: new set S11 (enrolment and transcript from two different universities, same student name and
     number): digital NEEDS_CORRECTION (INFORMATION_MISMATCH on university_name); scanned and photos
     NEEDS_CORRECTION or REVIEW_REQUIRED, never READY.
  3. Workflow: the student workflow compares university_name between 재학증명서 and 성적증명서 (value_type
     institution; see apps/api institution_key). Department stays uncompared (the transcript has no department field).
Hold-out sets receive change 1 only. Scanned and photo S09 expectations are unchanged.

    cd apps/api && PYTHONPATH=. python ../../evaluation/datasets/synthetic/make_manifests_v3.py [--holdout3]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "evaluation" / "harness"))

CHANGELOG = [
    {"id": "v3-1", "scope": "all corpora", "set": "S09", "version": "digital",
     "from": {"submission_status": "REVIEW_REQUIRED", "issue_codes": ["MISSING_REQUIRED_FIELD (student_id)"]},
     "to": {"submission_status": "READY", "issue_codes": []},
     "reason": "student-number rule corrected after the real-document finding (required on at least one document; compared only when both print it)",
     "note": "the v2 note 'must not be borrowed silently' is superseded by owner decision 2026-10-28"},
    {"id": "v3-2", "scope": "dev only", "set": "S11", "change": "new set: different universities, same student name and number",
     "digital": "NEEDS_CORRECTION (INFORMATION_MISMATCH university_name)", "scanned_and_photos": "NEEDS_CORRECTION or REVIEW_REQUIRED, never READY"},
    {"id": "v3-3", "scope": "workflow", "change": "university_name compared between 재학증명서 and 성적증명서; one-character differences go to review; department not compared"},
]


def build(corpus: str, dev_additions: bool) -> Path:
    root = HERE / corpus
    v2 = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    v3 = json.loads(json.dumps(v2))
    s09 = next(s for s in v3["student_sets"] if s["set_id"] == "S09")
    s09["expected"]["digital"] = {"submission_status": "READY", "issue_codes": []}
    s09["correct_behavior"] = (
        "v3: the student number is printed on the transcript only; the requirement is satisfied by any document of the submission, "
        "so the digital submission is READY. (v2 expected REVIEW_REQUIRED: 'must not be borrowed silently'.) Scans stay REVIEW_REQUIRED."
    )
    if dev_additions:
        add = json.loads((root / "student" / "S11_university_differs" / "v3_additions.json").read_text(encoding="utf-8"))
        v3["student_sets"].append({
            "set_id": "S11", "title": "Enrollment and transcript from two different universities, same student name", "workflow": "student",
            "submission_date": v2["submission_date"],
            "checklist_condition": "default student checklist: 재학증명서 required, 성적증명서 optional",
            "files": add["files"],
            "expected": {
                "digital": {"submission_status": "NEEDS_CORRECTION", "issue_codes": ["INFORMATION_MISMATCH (university_name)"]},
                "scanned": {"submission_status": "NEEDS_CORRECTION or REVIEW_REQUIRED, never READY", "issue_codes": []},
                "images": {"submission_status": "NEEDS_CORRECTION or REVIEW_REQUIRED, never READY", "issue_codes": []},
            },
            "correct_behavior": "v3 addition (dev only). Two universities under one name and one student number must never pass.",
            "current_behavior_per_audit": None, "known_bug_reference": None,
        })
        v3["files"].extend(add["entries"])
        v3["fictional_entities"]["student_second_university"] = {"university": "새빛가상대학교", "used_in": "S11 transcript"}
    v3["manifest_version"] = "v3"
    v3["v3_changelog"] = [c for c in CHANGELOG if dev_additions or c["scope"] != "dev only"]
    v3["v2_manifest_sha256"] = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    out = root / "manifest_v3.json"
    out.write_text(json.dumps(v3, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout3", action="store_true", help="also build hold-out 3's v3 manifest (opens it; logged by the guard)")
    a = ap.parse_args()
    rows = []
    for corpus, dev in (("test_variants", True), ("holdout", False), ("holdout2", False)):
        out = build(corpus, dev)
        rows.append((corpus, hashlib.sha256(out.read_bytes()).hexdigest()))
    if a.holdout3:
        import harness_core

        os.environ["ADVS_FINAL_JUDGEMENT"] = "1"
        harness_core.guard_corpus("holdout3")
        out = build("holdout3", False)
        rows.append(("holdout3", hashlib.sha256(out.read_bytes()).hexdigest()))
    for corpus, digest in rows:
        print(f"{corpus:14s} manifest_v3.json sha256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
