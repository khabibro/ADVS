import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.domain import EXPECTED_FIELDS, DocumentType, OverallStatus, ProcessingStatus
from app.document_intelligence.evidence import EvidenceRef
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.ocr.models import BoundingBox


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

    @classmethod
    def from_persisted(
        cls,
        document: Any,
        *,
        verification_status: OverallStatus | None = None,
        issues: list[str] | None = None,
    ) -> "CanonicalDocumentResult":
        """Reconstruct the canonical result without rerunning OCR.

        The persistence model deliberately remains outside the document-
        intelligence package. This adapter only relies on the documented
        attributes of a persisted Document and its ExtractedField rows.
        """
        extracted_fields = [
            ExtractedValue(
                field_name=row.field_name,
                raw_value=row.raw_value,
                normalized_value=row.normalized_value,
                confidence=row.confidence,
                needs_review=row.needs_review,
                extraction_method=row.extraction_method,
                source_text=row.source_text,
                evidence=[_evidence_from_dict(item) for item in row.evidence]
                if row.evidence
                else None,
            )
            for row in document.extracted_fields
        ]
        result = cls.compose(
            document_id=document.id,
            document_type=DocumentType(document.document_type),
            classification_confidence=document.classification_confidence,
            extracted_fields=extracted_fields,
            processing_status=ProcessingStatus(document.processing_status),
        )
        result.verification_status = verification_status
        result.issues = issues or []
        return result


def _evidence_from_dict(value: dict[str, Any]) -> EvidenceRef:
    bbox = value.get("bounding_box")
    return EvidenceRef(
        page_number=int(value["page_number"]),
        source_text=str(value["source_text"]),
        bounding_box=BoundingBox(**bbox) if bbox else None,
        confidence=value.get("confidence"),
        source_kind=value.get("source_kind", "ocr"),
        coordinate_space=value.get("coordinate_space", "pixel"),
    )
