"""Phase C safety items: business-number check digit (F-004). Values are hold-out values, not corpus values."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.core.domain import DocumentType, OverallStatus, ProcessingStatus, RuleType, Severity
from app.document_intelligence.evidence_sufficiency import (
    EffectiveValueSource,
    EvidenceAssessmentReason,
    EvidenceAssessmentState,
)
from app.document_intelligence.extraction.base import BRN_CHECKSUM_FAILED_METHOD
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.normalization.field_normalizer import is_valid_business_number
from app.document_intelligence.ocr.models import OCRDocumentResult, OCRLine, OCRPage
from app.document_intelligence.validation.engine import ValidationEngine
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    RequirementSnapshot,
    SubmissionRule,
    SubmissionVerificationEngine,
    VerificationContext,
)
from app.services.document_validation import policy_gated_fields

# ------------------------------------------------------------ C-3 / F-004

# 123-45-67891 is checksum-valid: sum(d*w)=165, +floor(9*5/10)=4 -> 169,
# (10 - 169 % 10) % 10 = 1. 214-86-55302 is a second valid number.
VALID_NUMBERS = ["123-45-67891", "1234567891", "214-86-55302"]


@pytest.mark.parametrize("number", VALID_NUMBERS)
def test_valid_business_numbers_pass(number: str) -> None:
    assert is_valid_business_number(number) is True


@pytest.mark.parametrize(
    "number", ["123-45-67890", "123-45-67892", "214-86-55303", "124-45-67891", "1234567890"]
)
def test_one_changed_digit_fails(number: str) -> None:
    assert is_valid_business_number(number) is False


def test_hyphenated_and_plain_forms_behave_the_same() -> None:
    for plain, hyphenated in (("1234567891", "123-45-67891"), ("1234567890", "123-45-67890")):
        assert is_valid_business_number(plain) == is_valid_business_number(hyphenated)


def test_malformed_input_is_not_valid() -> None:
    assert is_valid_business_number(None) is False
    assert is_valid_business_number("12-345-6789") is False
    assert is_valid_business_number("abc") is False


def _brn_value(number: str):
    text = f"납세증명서\n사업자등록번호 : {number}"
    page = OCRPage(
        1,
        text,
        [OCRLine(text=line) for line in text.splitlines()],
        metadata={"source": "direct_pdf_text"},
    )
    result = OCRDocumentResult("direct_pdf_text", [page], text)
    values = ExtractorRegistry().extract(DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE, result)
    return next(v for v in values if v.field_name == "business_registration_number")


def test_failing_checksum_keeps_value_and_marks_review() -> None:
    value = _brn_value("123-45-67890")
    assert value.normalized_value == "1234567890"
    assert value.raw_value == "123-45-67890"
    assert value.needs_review is True
    assert value.extraction_method == BRN_CHECKSUM_FAILED_METHOD


def test_valid_checksum_is_not_flagged() -> None:
    value = _brn_value("123-45-67891")
    assert value.normalized_value == "1234567891"
    assert value.needs_review is False
    assert value.extraction_method != BRN_CHECKSUM_FAILED_METHOD


def test_checksum_failure_survives_policy_gating_as_review_not_failure() -> None:
    gated = policy_gated_fields([_brn_value("123-45-67890")])[0]
    assert gated.normalized_value is None  # not trusted until a human confirms
    assert gated.extraction_method == BRN_CHECKSUM_FAILED_METHOD
    issues = ValidationEngine().validate_document(
        None,
        DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE,
        [gated],
    )
    codes = {i.code for i in issues if not i.passed}
    assert "BUSINESS_NUMBER_CHECKSUM_FAILED" in codes
    assert ValidationEngine().overall_status(issues) == OverallStatus.REVIEW_REQUIRED


def test_submission_reports_checksum_issue_as_review_required_never_ready_or_correction() -> None:
    snapshot = FieldSnapshot(
        uuid.uuid4(),
        "business_registration_number",
        None,
        True,
        True,
        EvidenceAssessmentState.REVIEW_REQUIRED,
        (EvidenceAssessmentReason.EXTRACTION_MARKED_FOR_REVIEW,),
        EffectiveValueSource.UNAVAILABLE,
        extraction_method=BRN_CHECKSUM_FAILED_METHOD,
    )
    document = DocumentSnapshot(
        uuid.uuid4(),
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        ProcessingStatus.COMPLETED,
        "abc",
        {"business_registration_number": snapshot},
    )
    requirement = RequirementSnapshot(
        uuid.uuid4(),
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        True,
        (),
        ("business_registration_number",),
    )
    result = SubmissionVerificationEngine().verify(
        project_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        requirements=[requirement],
        documents=[document],
        context=VerificationContext(date(2026, 3, 1)),
    )
    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert [i.code for i in result.issues] == ["BUSINESS_NUMBER_CHECKSUM_FAILED"]


def test_checksum_issue_is_reported_under_a_configured_required_field_rule() -> None:
    from app.core.domain import RuleType, Severity
    from app.document_intelligence.validation.engine import ConfiguredRule

    gated = policy_gated_fields([_brn_value("123-45-67890")])[0]
    rules = [ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.WARNING, {"field": "issue_date"})]
    issues = ValidationEngine().validate_document(
        None, DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE, [gated], configured_rules=rules
    )
    assert "BUSINESS_NUMBER_CHECKSUM_FAILED" in {i.code for i in issues if not i.passed}


def test_human_confirmed_value_clears_the_checksum_issue() -> None:
    snapshot = FieldSnapshot(
        uuid.uuid4(),
        "business_registration_number",
        "1234567890",
        True,
        True,
        EvidenceAssessmentState.SUFFICIENT,
        (),
        EffectiveValueSource.HUMAN_CONFIRMED,
        extraction_method=BRN_CHECKSUM_FAILED_METHOD,
    )
    result = SubmissionVerificationEngine()._unresolved_field(
        SubmissionRule(uuid.uuid4(), RuleType.REQUIRED_FIELD, Severity.WARNING, {}),
        DocumentSnapshot(
            uuid.uuid4(),
            DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
            ProcessingStatus.COMPLETED,
            "x",
            {},
        ),
        snapshot,
        "business_registration_number",
    )
    assert result is None
