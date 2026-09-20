import uuid

from app.core.domain import DocumentType, ProcessingStatus
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage
from app.document_intelligence.results import CanonicalDocumentResult


def _result(lines: list[OCRLine], *, page_number: int = 2, page_confidence: float = 0.99):
    page = OCRPage(
        page_number=page_number,
        text="\n".join(line.text for line in lines),
        lines=lines,
        confidence=page_confidence,
    )
    return OCRDocumentResult(provider="mock", pages=[page], assembled_text=page.text)


def test_normalization_preserves_raw_value_and_line_evidence() -> None:
    box = BoundingBox(x=12, y=34, width=200, height=18)
    source = _result([OCRLine("사업자등록번호 123-45-67890", 0.81, box)])
    fields = {
        field.field_name: field
        for field in ExtractorRegistry().extract(
            DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, source
        )
    }
    value = fields["business_registration_number"]
    assert value.raw_value == "123-45-67890"
    assert value.normalized_value == "1234567890"
    assert value.confidence == 0.81
    assert value.evidence is not None
    assert value.evidence[0].page_number == 2
    assert value.evidence[0].source_text == "사업자등록번호 123-45-67890"
    assert value.evidence[0].bounding_box == box
    assert value.evidence[0].confidence == 0.81


def test_multiple_lines_can_support_one_field_with_conservative_confidence() -> None:
    source = _result(
        [
            OCRLine("성명", 0.98, None),
            OCRLine("김학생", 0.42, BoundingBox(1, 2, 3, 4)),
        ]
    )
    fields = {
        field.field_name: field
        for field in ExtractorRegistry().extract(DocumentType.ENROLLMENT_CERTIFICATE, source)
    }
    student = fields["student_name"]
    assert student.normalized_value == "김학생"
    assert student.confidence == 0.42
    assert student.evidence is not None and len(student.evidence) == 2
    assert student.evidence[0].bounding_box is None


def test_high_page_confidence_does_not_fabricate_missing_gpa() -> None:
    source = _result(
        [
            OCRLine("성적증명서", 0.99, BoundingBox(0, 0, 100, 10)),
            OCRLine("성명 김학생", 0.98, BoundingBox(0, 20, 100, 10)),
        ],
        page_confidence=0.995,
    )
    fields = ExtractorRegistry().extract(DocumentType.TRANSCRIPT, source)
    canonical = CanonicalDocumentResult.compose(
        document_id=uuid.uuid4(),
        document_type=DocumentType.TRANSCRIPT,
        classification_confidence=0.99,
        extracted_fields=fields,
        processing_status=ProcessingStatus.EXTRACTING,
    )
    gpa = next(field for field in fields if field.field_name == "gpa")
    assert gpa.normalized_value is None
    assert gpa.confidence is None
    assert gpa.evidence is None
    assert "gpa" in canonical.missing_expected_fields


def test_unknown_has_no_expected_schema_or_fabricated_fields() -> None:
    fields = ExtractorRegistry().extract(
        DocumentType.UNKNOWN, _result([OCRLine("회의록", 0.99, None)])
    )
    canonical = CanonicalDocumentResult.compose(
        document_id=uuid.uuid4(),
        document_type=DocumentType.UNKNOWN,
        classification_confidence=0.0,
        extracted_fields=fields,
        processing_status=ProcessingStatus.EXTRACTING,
    )
    assert fields == []
    assert canonical.missing_expected_fields == []
