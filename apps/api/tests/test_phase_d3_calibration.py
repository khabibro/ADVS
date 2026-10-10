"""Phase D3 offline tools: calibrate_from_reviews and the conformal threshold utility (synthetic
records only)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation" / "harness"))

import calibrate_from_reviews as cr  # noqa: E402
import conformal  # noqa: E402


def test_review_analysis_counts_errors_confidence_bins_and_confusions() -> None:
    records = [
        {
            "field_name": "business_registration_number",
            "decision": "CONFIRMED",
            "original": "1234567891",
            "reviewed": None,
            "confidence": 0.97,
        },
        {
            "field_name": "business_registration_number",
            "decision": "CORRECTED",
            "original": "1234567891",
            "reviewed": "1234567891"[:3] + "8" + "1234567891"[4:],
            "confidence": 0.97,
        },
        {
            "field_name": "company_name",
            "decision": "CORRECTED",
            "original": "가온정밀",
            "reviewed": "가온정밀사",
            "confidence": 0.91,
        },
        {
            "field_name": "company_name",
            "decision": "REJECTED",
            "original": "x",
            "reviewed": None,
            "confidence": 0.5,
        },
    ]
    analysis = cr.analyse(records)
    brn = analysis["business_registration_number"]
    assert (brn["confirmed"], brn["corrected"]) == (1, 1)
    assert brn["confusions"][("4", "8")] == 1
    assert brn["bins"][3] == (1, 2)  # one wrong of two in [0.95, 0.98)
    assert analysis["company_name"]["length_changes"] == 1
    assert (
        analysis["company_name"]["confirmed"] + analysis["company_name"]["corrected"] == 1
    )  # REJECTED ignored
    text = cr.render(analysis)
    assert "4 → 8" in text and "No review decisions" not in text
    assert "No review decisions" in cr.render(cr.analyse([]))


def test_conformal_threshold_needs_enough_samples_and_respects_the_bound() -> None:
    assert conformal.required_samples(0.05) == 19
    few = [(0.95, True)] * 10
    assert conformal.threshold(few, 0.05)["threshold"] is None
    assert conformal.threshold(few, 0.05)["reason"] == "insufficient data"
    clean = [(0.90 + i / 1000, True) for i in range(40)]
    result = conformal.threshold(clean, 0.05)
    assert result["threshold"] == 0.90 and result["wrong"] == 0 and result["bound"] <= 0.05
    # a wrong value at high confidence forces the threshold above it (or no threshold at all)
    mixed = clean + [(0.99, False)]
    suggestion = conformal.threshold(mixed, 0.05)
    assert suggestion["threshold"] is None or suggestion["bound"] <= 0.05
    only_bad = [(0.9, False)] * 30
    assert conformal.threshold(only_bad, 0.05)["threshold"] is None


def test_suggestions_are_per_field_and_ignore_missing_confidence() -> None:
    records = [
        {"field_name": "gpa", "confidence": 0.9 + i / 1000, "correct": True} for i in range(30)
    ]
    records.append({"field_name": "gpa", "confidence": None, "correct": False})
    out = conformal.suggest(records, 0.1)
    assert set(out) == {"gpa"} and out["gpa"]["threshold"] is not None
    assert "gpa" in conformal.render(out, {"gpa": 0.9}, 0.1)
