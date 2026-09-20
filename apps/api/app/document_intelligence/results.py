import uuid
from dataclasses import dataclass, field

from app.core.domain import EXPECTED_FIELDS, DocumentType, OverallStatus, ProcessingStatus
from app.document_intelligence.extraction.base import ExtractedValue


@dataclass
class CanonicalDocumentResult:
    """Canonical, provider-independent result of processing one document."""

    document_id: uuid.UUID
    document_type: DocumentType
    classification_confidence: float | None
    extracted_fields: list[ExtractedValue]
    processing_status: ProcessingStatus
    missing_expected_fields: list[str] = field(default_factory=list)
    verification_status: OverallStatus | None = None
    issues: list[str] = field(default_factory=list)

    @classmethod
    def compose(
        cls,
        *,
        document_id: uuid.UUID,
        document_type: DocumentType,
        classification_confidence: float | None,
        extracted_fields: list[ExtractedValue],
        processing_status: ProcessingStatus,
    ) -> "CanonicalDocumentResult":
        extracted = {
            item.field_name for item in extracted_fields if item.normalized_value is not None
        }
        missing = [name for name in EXPECTED_FIELDS[document_type] if name not in extracted]
        return cls(
            document_id=document_id,
            document_type=document_type,
            classification_confidence=classification_confidence,
            extracted_fields=extracted_fields,
            processing_status=processing_status,
            missing_expected_fields=missing,
        )
