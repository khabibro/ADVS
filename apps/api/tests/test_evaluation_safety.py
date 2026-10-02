import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from eval_lib.safety import field_verdict, score_run  # noqa: E402


def test_absence_and_ambiguity_are_distinct():
    assert field_verdict({"gt": "VERIFIED_ABSENT"}, None) == "CORRECTLY_ABSTAINED"
    assert field_verdict({"state": "NOT_EVIDENCED"}, "4.5") == "INCORRECT"
    assert field_verdict({"state": "AMBIGUOUS"}, None) == "AMBIGUOUS_GROUND_TRUTH"
    assert field_verdict(None, "value") == "NOT_EVALUATED"
    assert field_verdict({"state": "PRESENT", "value": "-1"}, "1") == "INCORRECT"
    assert (
        field_verdict(
            {"state": "PRESENT", "value": "900-80-10000"},
            "9008010000",
            "business_registration_number",
        )
        == "CORRECT"
    )
    assert (
        field_verdict({"state": "PRESENT", "value": "ACME-21"}, "ACME21", "company_name")
        == "INCORRECT"
    )


def test_fixed_denominator_unlabelled_outputs_and_negative_assertions():
    gold = {
        "dataset_version": "test-v1",
        "gold_version": "test-v1",
        "samples": {
            "A": {
                "document_type": "UNKNOWN",
                "fields": {"x": {"state": "PRESENT", "value": "1", "required": True}},
                "negative_assertions": [{"field": "unexpected", "must_not_equal": "bad"}],
            },
            "B": {
                "document_type": "UNKNOWN",
                "fields": {"x": {"state": "PRESENT", "value": "2", "required": True}},
            },
        },
    }
    run = {
        "samples": [
            {
                "sample_id": "A",
                "processing_status": "COMPLETED",
                "fields": {"x": {"value": "1"}, "unexpected": {"value": "bad"}},
                "negative_assertions": [{"field": "unexpected", "violated": False}],
            }
        ]
    }
    unchanged = copy.deepcopy((run, gold))
    result = score_run(run, gold)
    assert result["metrics"]["SUPPORTED_FIELD_PRECISION"] == 0.5
    assert result["metrics"]["SUPPORTED_FIELD_RECALL"] == 0.5
    assert result["counts"]["negative_violations"] == 1
    assert result["counts"]["populated_unlabelled"] == 1
    assert result["metrics"]["UNRESOLVED_REQUIRED_COUNT"] == 1
    assert (run, gold) == unchanged
    assert result["metrics"]["FALSE_READY_COUNT"] is None


def test_ready_requires_supported_required_values_under_explicit_profile():
    gold = {
        "dataset_version": "v1",
        "gold_version": "v1",
        "samples": {
            "A": {
                "document_type": "X",
                "fields": {
                    "required": {"state": "PRESENT", "value": "value", "required": True},
                    "optional": {"state": "PRESENT", "value": "other", "required": False},
                },
            }
        },
    }
    run = {"samples": [{"sample_id": "A", "project_status": "READY", "fields": {}}]}
    assert score_run(run, gold)["metrics"]["FALSE_READY_COUNT"] == 1
    run["samples"][0]["fields"] = {"required": {"value": "value"}}
    assert score_run(run, gold)["metrics"]["FALSE_READY_COUNT"] == 0
