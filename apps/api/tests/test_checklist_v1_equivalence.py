"""Version 1 of each checklist compiles to what the seeded rows produced.

Allowed differences (decided with the owner, see docs/planning/ADMIN_WEB_DESIGN.md section 3.2):
the student checklist drops the two ``issue_date <= 2026-12-31`` rows and the 학번 requirement of
the 재학증명서. Nothing else may differ.
"""

import json
from importlib import resources

import pytest

from app.checklists.compile import compile_checklist
from app.checklists.schema import parse_document
from app.services.verification import SubmissionVerificationService
from tests.legacy_rows import legacy_business, legacy_student


def load_template(name: str):
    raw = json.loads(resources.files("app.checklists.templates").joinpath(name).read_text("utf-8"))
    document, problems = parse_document(raw)
    assert not problems and document is not None
    return document


def comparable(requirements):
    """Requirements without row/derived ids, in a stable order."""
    out = {}
    for item in requirements:
        rules = sorted(
            (rule.rule_type.value, rule.severity.value, json.dumps(rule.params, sort_keys=True))
            for rule in item.rules
        )
        out[item.document_type.value] = {
            "required": item.required,
            "required_fields": list(item.required_fields),
            "rules": rules,
        }
    return out


def test_business_v1_equals_seeded_rules():
    legacy = SubmissionVerificationService()._requirements(legacy_business())
    compiled = compile_checklist(load_template("business.v1.json")).requirements
    assert comparable(compiled) == comparable(legacy)


def test_student_v1_equals_seeded_rules_except_the_two_decided_changes():
    legacy = comparable(SubmissionVerificationService()._requirements(legacy_student()))
    # apply the decided changes to the legacy expectation
    year_end = [r for r in legacy["ENROLLMENT_CERTIFICATE"]["rules"] if "2026-12-31" in r[2]]
    assert len(year_end) == 1
    legacy["ENROLLMENT_CERTIFICATE"]["rules"] = [
        r for r in legacy["ENROLLMENT_CERTIFICATE"]["rules"] if "2026-12-31" not in r[2]
    ]
    legacy["TRANSCRIPT"]["rules"] = [
        r for r in legacy["TRANSCRIPT"]["rules"] if "2026-12-31" not in r[2]
    ]
    assert "student_id" in legacy["ENROLLMENT_CERTIFICATE"]["required_fields"]
    legacy["ENROLLMENT_CERTIFICATE"]["required_fields"].remove("student_id")
    compiled = compile_checklist(load_template("student.v1.json")).requirements
    assert comparable(compiled) == legacy


def test_rule_ids_are_stable_across_compiles():
    document = load_template("student.v1.json")
    first = compile_checklist(document).requirements
    second = compile_checklist(document).requirements
    assert [r.id for r in first] == [r.id for r in second]
    assert [x.id for r in first for x in r.rules] == [x.id for r in second for x in r.rules]


@pytest.mark.parametrize("name", ["business.v1.json", "student.v1.json"])
def test_templates_pass_the_engine_configuration_check(name):
    from app.document_intelligence.validation.submission import SubmissionVerificationEngine

    SubmissionVerificationEngine().validate_configuration(
        compile_checklist(load_template(name)).requirements
    )
