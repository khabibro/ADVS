import uuid
from datetime import UTC, datetime

import pytest

from app.core.domain import DOCUMENT_TYPE_DISPLAY_NAMES, EXPECTED_FIELDS, DocumentType
from app.schemas.api import DocumentRead

MENTOR_TYPES = {
    DocumentType.BUSINESS_REGISTRATION_CERTIFICATE: (
        "사업자등록증",
        {"company_name", "business_registration_number"},
    ),
    DocumentType.SME_CONFIRMATION_CERTIFICATE: (
        "중소기업확인서",
        {"company_name", "business_registration_number", "valid_from", "valid_until"},
    ),
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE: (
        "국세 납세증명서",
        {"company_name", "business_registration_number", "valid_until"},
    ),
    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE: (
        "4대 사회보험료 완납증명서",
        {"workplace_name", "business_registration_number", "valid_until"},
    ),
    DocumentType.ENROLLMENT_CERTIFICATE: (
        "재학증명서",
        {"student_name", "university_name", "department", "student_id", "issue_date"},
    ),
    DocumentType.TRANSCRIPT: (
        "성적증명서",
        {"student_name", "university_name", "student_id", "issue_date", "gpa"},
    ),
}


@pytest.mark.parametrize(("document_type", "expected"), MENTOR_TYPES.items())
def test_mentor_document_types_have_display_names_and_fields(
    document_type: DocumentType, expected: tuple[str, set[str]]
) -> None:
    display_name, required_fields = expected
    assert DocumentType(document_type.value) is document_type
    assert DOCUMENT_TYPE_DISPLAY_NAMES[document_type] == display_name
    assert required_fields <= set(EXPECTED_FIELDS[document_type])


def test_existing_and_unknown_document_types_remain_supported() -> None:
    assert DOCUMENT_TYPE_DISPLAY_NAMES[DocumentType.GRADUATION_CERTIFICATE] == "졸업증명서"
    assert DOCUMENT_TYPE_DISPLAY_NAMES[DocumentType.CAREER_CERTIFICATE] == "경력증명서"
    assert DOCUMENT_TYPE_DISPLAY_NAMES[DocumentType.UNKNOWN] == "알 수 없는 문서"
    assert EXPECTED_FIELDS[DocumentType.UNKNOWN] == []


def test_document_api_serializes_enum_and_canonical_display_name() -> None:
    payload = DocumentRead(
        id=uuid.uuid4(),
        original_filename="unknown.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        processing_status="COMPLETED",
        processing_version=0,
        document_type=DocumentType.UNKNOWN,
        classification_confidence=None,
        error_code=None,
        error_message=None,
        created_at=datetime.now(UTC),
    ).model_dump(mode="json")
    assert payload["document_type"] == "UNKNOWN"
    assert payload["document_type_display_name"] == "알 수 없는 문서"
