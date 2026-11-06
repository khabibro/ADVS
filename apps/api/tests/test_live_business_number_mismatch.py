"""Two business numbers that are each confident (floor, check digit) but differ are another business: 보완 필요,
not an endless review. Invented numbers (valid check digits)."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.domain import DocumentType, OverallStatus, RuleOperator, RuleType, Severity
from app.document_intelligence.evidence_sufficiency import EvidenceAssessmentState
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    ProcessingStatus,
    RequirementSnapshot,
    SubmissionRule,
    SubmissionVerificationEngine,
    VerificationContext,
)

BRC = DocumentType.BUSINESS_REGISTRATION_CERTIFICATE
NTAX = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE


def _doc(kind, number, accepted=True, reason=None):
    field = FieldSnapshot(
        uuid.uuid4(),
        "business_registration_number",
        number if accepted else None,
        False,
        True,
        EvidenceAssessmentState.SUFFICIENT if accepted else EvidenceAssessmentState.REVIEW_REQUIRED,
        machine_value=number,
        auto_reason=reason,
    )
    return DocumentSnapshot(
        uuid.uuid4(),
        kind,
        ProcessingStatus.COMPLETED,
        uuid.uuid4().hex,
        {"business_registration_number": field},
    )


def _verify(a, b):
    rule = SubmissionRule(
        uuid.uuid4(),
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": BRC.value,
            "source_field": "business_registration_number",
            "target_document_type": NTAX.value,
            "target_field": "business_registration_number",
            "operator": RuleOperator.EQUALS.value,
            "value_type": "identifier",
        },
    )
    requirements = [
        RequirementSnapshot(uuid.uuid4(), BRC, True, (rule,)),
        RequirementSnapshot(uuid.uuid4(), NTAX, True, ()),
    ]
    return SubmissionVerificationEngine().verify(
        project_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        requirements=requirements,
        documents=[a, b],
        context=VerificationContext(date(2026, 11, 6)),
    )


def test_two_confident_numbers_that_differ_need_correction() -> None:
    result = _verify(
        _doc(BRC, "1234567004", False, "DISAGREES_WITH_OTHER_DOCUMENT"),
        _doc(NTAX, "2345678001", False, "DISAGREES_WITH_OTHER_DOCUMENT"),
    )
    assert result.status == OverallStatus.NEEDS_CORRECTION
    assert [i.code for i in result.issues] == ["INFORMATION_MISMATCH"]


def test_a_number_held_back_for_another_reason_stays_a_review() -> None:
    result = _verify(
        _doc(BRC, "1234567004", False, "CONFIDENCE_BELOW_FLOOR"),
        _doc(NTAX, "2345678001", False, "DISAGREES_WITH_OTHER_DOCUMENT"),
    )
    assert result.status != OverallStatus.NEEDS_CORRECTION


def test_a_number_with_a_bad_check_digit_is_never_a_mismatch() -> None:
    result = _verify(
        _doc(BRC, "1234567005", False, "DISAGREES_WITH_OTHER_DOCUMENT"),
        _doc(NTAX, "2345678001", False, "DISAGREES_WITH_OTHER_DOCUMENT"),
    )
    assert result.status != OverallStatus.NEEDS_CORRECTION


def test_equal_numbers_pass() -> None:
    result = _verify(_doc(BRC, "1234567004"), _doc(NTAX, "1234567004"))
    assert result.status == OverallStatus.READY
