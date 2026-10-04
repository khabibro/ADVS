"""B-3 (audit F-003): real Korean documents this system does not model,
whose titles happen to overlap with a modeled type's signals, must never
be confidently classified as that modeled type.

지방세 납세증명서 (local tax) was being classified as
NATIONAL_TAX_PAYMENT_CERTIFICATE (국세, a different certificate) at
confidence 0.9 with needs_review=False, because "납세증명서" is a
TITLE-weight signal matched by plain substring containment, and
"지방세납세증명서" contains it. DECISION_2 (UNDECIDED -> default applied):
these documents get UNKNOWN with needs_review=True; no new document type
is added for them.
"""

from __future__ import annotations

from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import DocumentClassifier

LOCAL_TAX_TEXT = "지방세 납세증명서\n납세자명 한국테크\n유효기한 2026-12-31"
LEAVE_OF_ABSENCE_TEXT = "휴학증명서\n성명 김학생\n대학교 한국대학교\n학번 20260001"
EXPECTED_GRADUATION_TEXT = "졸업예정증명서\n성명 김학생\n대학교 한국대학교\n학과 컴퓨터공학과"

NATIONAL_TAX_TEXT = "국세 납세증명서\n납세자명 한국테크\n사업자등록번호 123-45-67890"
ENROLLMENT_TEXT = "재학증명서\n성명 김학생\n대학교 한국대학교\n학번 20260001"
GRADUATION_TEXT = (
    "졸업증명서\n성명 홍길동\n대학교 한국대학교\n학과 컴퓨터공학과\n학위 학사\n졸업일자 2024-02-20"
)


def test_local_tax_certificate_is_unknown_not_national_tax() -> None:
    result = DocumentClassifier().classify(LOCAL_TAX_TEXT)
    assert result.predicted_type == DocumentType.UNKNOWN
    assert result.needs_review is True


def test_leave_of_absence_certificate_is_unknown_not_enrollment() -> None:
    result = DocumentClassifier().classify(LEAVE_OF_ABSENCE_TEXT)
    assert result.predicted_type == DocumentType.UNKNOWN
    assert result.needs_review is True


def test_expected_graduation_certificate_is_unknown_not_graduation() -> None:
    result = DocumentClassifier().classify(EXPECTED_GRADUATION_TEXT)
    assert result.predicted_type == DocumentType.UNKNOWN
    assert result.needs_review is True


def test_genuine_national_tax_certificate_still_classifies_correctly() -> None:
    result = DocumentClassifier().classify(NATIONAL_TAX_TEXT)
    assert result.predicted_type == DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
    assert result.needs_review is False


def test_genuine_enrollment_certificate_still_classifies_correctly() -> None:
    result = DocumentClassifier().classify(ENROLLMENT_TEXT)
    assert result.predicted_type == DocumentType.ENROLLMENT_CERTIFICATE
    assert result.needs_review is False


def test_genuine_graduation_certificate_still_classifies_correctly() -> None:
    result = DocumentClassifier().classify(GRADUATION_TEXT)
    assert result.predicted_type == DocumentType.GRADUATION_CERTIFICATE
    assert result.needs_review is False


def test_lookalike_check_does_not_trigger_on_the_genuine_document() -> None:
    """A national-tax certificate's own text must not itself contain a
    look-alike marker and get wrongly routed to UNKNOWN."""
    for text in (NATIONAL_TAX_TEXT, ENROLLMENT_TEXT, GRADUATION_TEXT):
        result = DocumentClassifier().classify(text)
        assert result.predicted_type != DocumentType.UNKNOWN
