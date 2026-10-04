"""Maintain sanitized failure history, including fixed failures and abstentions."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAUSES = {
    ("ASTRA-R01", "business_registration_number"): ("OCR_RECOGNITION", "The number is present, but the adjacent business-number label loses a Hangul character. Competing management identifier makes fuzzy recovery unsafe."),
    ("ASTRA-R01", "issue_date"): ("SEMANTIC_INFERENCE", "The original has repeated unlabelled date statements; baseline inference declines multiple observations. No evidence justifies choosing another semantic date."),
    ("ASTRA-R02", "company_name"): ("LABEL_DETECTION", "The company value survives OCR under a legal-entity-name label outside the extractor label vocabulary."),
    ("ASTRA-R02", "representative_name"): ("OCR_SEGMENTATION", "The letter-spaced representative label is incompletely boxed and reconstructed; its value also requires glyph adjudication."),
    ("ASTRA-R02", "issue_date"): ("SEMANTIC_INFERENCE", "A bare signature-block date is visible, but the conservative issuer-context inference does not accept the OCR observation."),
    ("ASTRA-R02", "business_address"): ("OCR_RECOGNITION", "A correctly detected complete address line has one Hangul glyph substitution. The candidate and evidence identify the correct source row; normalization does not introduce the substitution."),
    ("ASTRA-R03", "student_name"): ("EVALUATION_HARNESS", "Prior gold and OCR disagree on one low-resolution surname glyph. Independent visual inspection cannot confidently adjudicate it; gold is now explicitly ambiguous, with old assertion retained for sensitivity analysis."),
    ("ASTRA-R03", "gpa"): ("TABLE_STRUCTURE", "Overall GPA label and its value occupy different header table rows, alongside many term averages. Flat row association cannot establish the intended cell relation safely."),
    ("ASTRA-R03", "gpa_scale"): ("TABLE_STRUCTURE", "Overall GPA scale is visibly printed in the same numeric cell; old gold incorrectly called it not evidenced. Corrected gold still leaves table association unresolved."),
    ("ASTRA-R03", "issue_date"): ("SEMANTIC_INFERENCE", "Multiple date contexts and an unlabelled issue-date signature block require explicit semantic association; current inference abstains."),
    ("ASTRA-R04", "student_name"): ("OCR_SEGMENTATION", "One detector box spans fragments of two header labels across rows. Value text survives but the label-to-cell relation is destroyed before extraction."),
    ("ASTRA-R04", "student_id"): ("OCR_SEGMENTATION", "Merged header-label glyphs prevent reliable reconstruction of the student-ID cell relation, although the identifier itself is recognized."),
    ("ASTRA-R04", "university_name"): ("FIELD_CANDIDATE_GENERATION", "Institution text survives in a stamp-overlapped signature block, but extra corrupted issuer text prevents the conservative institution candidate from being accepted."),
    ("ASTRA-R05", "university_name"): ("FIELD_CANDIDATE_GENERATION", "Institution is a standalone signature, not a university-name label followed by value. The enrollment extractor lacks that explicit semantic strategy."),
    ("ASTRA-R05", "department"): ("LABEL_DETECTION", "The clearly printed faculty/department uses the affiliation label; current enrollment label schema only accepts department/major labels."),
    ("ASTRA-R06", "representative_name"): ("FIELD_CANDIDATE_PAIRING", "Label and value survive OCR in separate boxes, but no usable representative candidate is selected. Precise ranking subcause remains unproven; retaining null is safer than forced recovery."),
    ("ASTRA-R07", "university_name"): ("FIELD_CANDIDATE_GENERATION", "Institution survives in a signature block with corrupted issuer suffix; enrollment's label-value strategy does not accept the standalone institution."),
    ("ASTRA-R07", "department"): ("SEMANTIC_INFERENCE", "Affiliation, primary major, and double major are all printed. A single department field has no independently adjudicated meaning here."),
}


def main():
    before = json.loads((ROOT / "realistic_before.json").read_text())
    after_path = ROOT / "realistic_after.json"
    after = json.loads(after_path.read_text()) if after_path.exists() else before
    current = {(d["sample_id"], f["field"]): f for d in after["documents"] for f in d["fields"]}
    entries = []
    for document in before["documents"]:
        for field in document["fields"]:
            if field["verdict"] not in {"INCORRECT", "UNRESOLVED", "AMBIGUOUS_GROUND_TRUTH", "CORRECTLY_ABSTAINED"}:
                continue
            key = (document["sample_id"], field["field"])
            final = current[key]
            if field["verdict"] == "CORRECTLY_ABSTAINED":
                stage, cause = "VALUE_VALIDATION", "Source does not supply this field. Null is the supported outcome; no date or identifier may be invented."
            else:
                stage, cause = CAUSES.get(key, ("SEMANTIC_INFERENCE", "Ambiguous source semantics; no unique field assertion is supported."))
            status = "FIXED" if final["verdict"] == "CORRECT" else "ACCEPTED_ABSTENTION" if final["verdict"] in {"CORRECTLY_ABSTAINED", "AMBIGUOUS_GROUND_TRUTH"} else "REMAINING"
            entry = {"sample_id": key[0], "document_type": document["document_type"], "field": key[1],
                     "expected_state": field["expected_state"], "actual_state": final["verdict"],
                     "before_state": field["verdict"], "earliest_failure_stage": stage,
                     "downstream_effect": "Unsupported populated value" if final["verdict"] == "INCORRECT" else "Coverage/review burden; deterministic verification must abstain",
                     "severity": "HIGH" if final["verdict"] == "INCORRECT" else "MEDIUM",
                     "false_non_null": final["verdict"] == "INCORRECT",
                     "status_impact": "Must block READY if required by selected workflow" if field["required"] else "Optional field: review without automatic readiness block",
                     "evidence_quality": final.get("evidence_assessment"), "reproduced": True,
                     "root_cause": cause, "candidate_fix": "Conservative evidence review; independently evaluate richer geometry/provider before adding extraction heuristics",
                     "regression_risk": "Over-association of neighboring cells or semantic dates creates plausible wrong values",
                     "status": status}
            if key == ("ASTRA-R02", "business_address"):
                entry["visual_trace"] = {"original_inspected": True, "detection_correct": True,
                    "recognition_correct": False, "geometry_correct": True, "reading_order_correct": True,
                    "label_recognized": True, "correct_semantic_candidate_generated": True,
                    "wrong_candidate_reason": "Correct row contains recognizer glyph substitution",
                    "normalization_corrupted": False, "baseline_evidence_policy_accepted": True,
                    "existing_signal_limitation": "Recognition score 0.9119 cannot validate address identity",
                    "overlay_location": "Private evaluation directory only"}
            entries.append(entry)
    for sid, field, stage, cause, test in [
        ("ASTRA-S01", "valid_until", "NORMALIZATION", "Global dash folding destroyed range boundaries; fallback selected the first date as expiry.", "test_range_endpoints_remain_distinct"),
        ("ASTRA-S02", "graduation_date", "SEMANTIC_INFERENCE", "Shared generic date-field helper applied issue-date inference to unrelated date semantics.", "test_issue_date_does_not_supply_graduation_or_employment_or_validity"),
        ("ASTRA-S03", "employment_start_date/employment_end_date", "SEMANTIC_INFERENCE", "Issue-date inference populated both employment endpoints and shadowed an explicit employment range.", "test_issue_date_does_not_shadow_employment_range"),
        ("ASTRA-S04", "source_kind/coordinate_space", "EVIDENCE_ASSOCIATION", "Document-wide mixed provider marker mislabelled embedded PDF evidence as OCR pixels.", "test_mixed_source_provenance_is_per_evidence_page"),
    ]:
        entries.append({"sample_id": sid, "document_type": "SYNTHETIC_REGRESSION", "field": field,
            "expected_state": "SUPPORTED_FIELD_SEMANTICS", "actual_state": "CORRECT", "earliest_failure_stage": stage,
            "downstream_effect": "Plausible wrong field or dishonest evidence", "severity": "CRITICAL", "false_non_null": sid != "ASTRA-S04",
            "status_impact": "Potential false deterministic decision", "evidence_quality": "Regression-tested",
            "reproduced": True, "root_cause": cause, "candidate_fix": "Implemented field-aware normalization/scoped inference/per-page provenance",
            "regression_risk": "Positive and negative behavior tests required", "status": "FIXED", "regression_test": test})
    (ROOT / "failure_ledger.json").write_text(json.dumps({"schema_version": "astra-ledger-1", "gold_version": before["ground_truth_version"], "entries": entries}, indent=2)+"\n")


if __name__ == "__main__":
    main()
