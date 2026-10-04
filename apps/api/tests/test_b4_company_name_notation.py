"""B-4 (audit F-002): company names written with different Korean
legal-entity notation (주식회사 X / (주)X / X(주) / 유X) must compare equal.

Covers both real comparison paths:
- the submission-level FIELD_COMPARISON rule
  (validation/submission.py::_field_comparison / _comparison_key), which is
  what the actual seeded business checklist uses to compare a document's
  company_name/workplace_name against the reference 사업자등록증 -- this is
  the path a real B02-style submission goes through;
- the per-document project-level company_name check
  (validation/engine.py::ValidationEngine.validate_document's
  COMPANY_NAME_MATCH), a separate mechanism (project.company_name vs a
  document's own field) that uses the same `comparable()` utility.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.core.domain import DocumentType, OverallStatus, RuleOperator, RuleType, Severity
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.validation.engine import ValidationEngine
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    ProcessingStatus,
    RequirementSnapshot,
    SubmissionRule,
    SubmissionVerificationEngine,
    VerificationContext,
)

EVALUATION_DATE = date(2026, 10, 5)
PROJECT_ID = uuid.UUID(int=1)
WORKFLOW_ID = uuid.UUID(int=2)

NOTATIONS = [
    "주식회사 테스트상사",
    "(주)테스트상사",
    "㈜테스트상사",
    "테스트상사(주)",
]


def _field(name: str, value: str | None) -> FieldSnapshot:
    return FieldSnapshot(uuid.uuid4(), name, value, False, value is not None)


def _document(document_type: DocumentType, values: dict[str, str | None]) -> DocumentSnapshot:
    return DocumentSnapshot(
        uuid.uuid4(),
        document_type,
        ProcessingStatus.COMPLETED,
        uuid.uuid4().hex,
        {name: _field(name, value) for name, value in values.items()},
    )


def _field_comparison_rule(
    target_type: DocumentType, source_field: str, target_field: str
) -> SubmissionRule:
    return SubmissionRule(
        uuid.uuid4(),
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value,
            "source_field": source_field,
            "target_document_type": target_type.value,
            "target_field": target_field,
            "operator": RuleOperator.EQUALS.value,
            "value_type": "string",
        },
    )


def _verify(requirements, documents):
    return SubmissionVerificationEngine().verify(
        project_id=PROJECT_ID,
        workflow_id=WORKFLOW_ID,
        requirements=requirements,
        documents=documents,
        context=VerificationContext(EVALUATION_DATE),
    )


def _issue_codes(result) -> set[str]:
    return {item.code for item in result.issues}


@pytest.mark.parametrize("notation", NOTATIONS[1:])
def test_all_notations_of_the_same_company_compare_equal(notation: str) -> None:
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = _verify(
        [
            RequirementSnapshot(
                uuid.uuid4(), DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, True, ()
            ),
            RequirementSnapshot(
                uuid.uuid4(),
                target_type,
                True,
                (_field_comparison_rule(target_type, "company_name", "company_name"),),
            ),
        ],
        [
            _document(
                DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, {"company_name": NOTATIONS[0]}
            ),
            _document(target_type, {"company_name": notation}),
        ],
    )
    assert "INFORMATION_MISMATCH" not in _issue_codes(result)


def test_a_name_that_merely_contains_the_syllable_ju_is_not_altered() -> None:
    """Guard: 주원상사 does not start with 주식회사/(주)/㈜, and 한주테크 does
    not end with any marker -- neither may be mistaken for a notation
    variant of the other, or of anything else."""
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = _verify(
        [
            RequirementSnapshot(
                uuid.uuid4(), DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, True, ()
            ),
            RequirementSnapshot(
                uuid.uuid4(),
                target_type,
                True,
                (_field_comparison_rule(target_type, "company_name", "company_name"),),
            ),
        ],
        [
            _document(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, {"company_name": "주원상사"}),
            _document(target_type, {"company_name": "한주테크"}),
        ],
    )
    assert "INFORMATION_MISMATCH" in _issue_codes(result)
    assert result.status == OverallStatus.NEEDS_CORRECTION


def test_genuinely_different_companies_still_mismatch() -> None:
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = _verify(
        [
            RequirementSnapshot(
                uuid.uuid4(), DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, True, ()
            ),
            RequirementSnapshot(
                uuid.uuid4(),
                target_type,
                True,
                (_field_comparison_rule(target_type, "company_name", "company_name"),),
            ),
        ],
        [
            _document(
                DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
                {"company_name": "주식회사 테스트상사"},
            ),
            _document(target_type, {"company_name": "가나다솔루션"}),
        ],
    )
    # DECISION_1 (UNDECIDED -> default): a remaining mismatch after
    # normalization is still NEEDS_CORRECTION.
    assert "INFORMATION_MISMATCH" in _issue_codes(result)
    assert result.status == OverallStatus.NEEDS_CORRECTION


def test_business_registration_number_comparison_is_unaffected() -> None:
    """The normalization is scoped to company_name/workplace_name notation
    only -- it must not change how identifier-typed fields compare."""
    target_type = DocumentType.SME_CONFIRMATION_CERTIFICATE
    result = _verify(
        [
            RequirementSnapshot(
                uuid.uuid4(), DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, True, ()
            ),
            RequirementSnapshot(
                uuid.uuid4(),
                target_type,
                True,
                (
                    SubmissionRule(
                        uuid.uuid4(),
                        RuleType.FIELD_COMPARISON,
                        Severity.ERROR,
                        {
                            "source_document_type": DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value,
                            "source_field": "business_registration_number",
                            "target_document_type": target_type.value,
                            "target_field": "business_registration_number",
                            "operator": RuleOperator.EQUALS.value,
                            "value_type": "identifier",
                        },
                    ),
                ),
            ),
        ],
        [
            _document(
                DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
                {"business_registration_number": "123-45-00018"},
            ),
            _document(target_type, {"business_registration_number": "123-45-00019"}),
        ],
    )
    assert "INFORMATION_MISMATCH" in _issue_codes(result)


# ---------------------------------------------------------------------
# Per-document project-level COMPANY_NAME_MATCH (validation/engine.py)
# ---------------------------------------------------------------------


@pytest.mark.parametrize("notation", NOTATIONS)
def test_engine_level_company_name_match_ignores_notation(notation: str) -> None:
    fields = [ExtractedValue("company_name", notation, notation)]
    issues = ValidationEngine().validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        fields,
        company_name="주식회사 테스트상사",
        configured_rules=[],
    )
    mismatches = [i for i in issues if i.code == "COMPANY_NAME_MISMATCH"]
    assert mismatches == []
