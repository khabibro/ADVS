import logging
import time
import uuid
from dataclasses import asdict

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.domain import DocumentType, ProcessingStatus, RuleType, Severity
from app.core.errors import PROCESSING_ERROR_MESSAGES, ProcessingErrorCode
from app.document_intelligence.classification.classifier import (
    ClassificationResult,
    DocumentClassifier,
)
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.models import OCRDocumentResult, OCRProviderError
from app.document_intelligence.ocr.providers import get_ocr_provider
from app.document_intelligence.ocr.text_assembly import assemble_document_text
from app.document_intelligence.preprocessing.processor import PdfProcessor
from app.document_intelligence.results import CanonicalDocumentResult
from app.document_intelligence.validation.engine import (
    ConfiguredRule,
    ValidationEngine,
    ValidationIssue,
)
from app.models.entities import (
    Document,
    DocumentRequirement,
    ExtractedField,
    OCRResult,
    Project,
    Submission,
    ValidationResult,
    ValidationRule,
)
from app.services.storage.local import LocalStorageService
from app.services.verification import invalidate_document_project_verification

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = {
    ProcessingStatus.PREPROCESSING,
    ProcessingStatus.OCR_PENDING,
    ProcessingStatus.OCR_PROCESSING,
    ProcessingStatus.OCR_COMPLETED,
    ProcessingStatus.CLASSIFYING,
    ProcessingStatus.EXTRACTING,
    ProcessingStatus.VALIDATING,
}


class DocumentProcessingService:
    """The single authoritative orchestration path for a stored document.

    Algorithms remain in ``document_intelligence``. This service chooses the
    source path, coordinates each stage, and atomically replaces all derived
    persistence on success. A failed attempt clears derived state rather than
    exposing a new classification beside stale fields from an older run.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = LocalStorageService(self.settings)
        self.pdf = PdfProcessor()
        self.classifier = DocumentClassifier()
        self.extractor = ExtractorRegistry()
        self.validator = ValidationEngine()

    async def process(self, db: Session, document_id: uuid.UUID) -> Document:
        document = db.get(Document, document_id)
        if not document:
            raise ValueError("document not found")
        if ProcessingStatus(document.processing_status) in _ACTIVE_STATUSES:
            return document

        started = time.perf_counter()
        claimed_document_id = db.scalar(
            update(Document)
            .where(
                Document.id == document.id,
                Document.processing_status.not_in([status.value for status in _ACTIVE_STATUSES]),
            )
            .values(
                processing_status=ProcessingStatus.PREPROCESSING,
                error_code=None,
                error_message=None,
            )
            .returning(Document.id)
        )
        db.commit()
        if claimed_document_id is None:
            db.refresh(document)
            return document
        invalidate_document_project_verification(db, document)
        db.commit()
        db.refresh(document)
        logger.info("document_processing_started", extra={"document_id": str(document.id)})

        try:
            source_result = await self._obtain_source(db, document)

            self._set_status(db, document, ProcessingStatus.CLASSIFYING)
            classification = self.classifier.classify(
                source_result.assembled_text, document.original_filename
            )
            logger.info(
                "classification_completed",
                extra={
                    "document_id": str(document.id),
                    "document_type": str(classification.predicted_type),
                    "needs_review": classification.needs_review,
                },
            )

            self._set_status(db, document, ProcessingStatus.EXTRACTING)
            fields = self.extractor.extract(classification.predicted_type, source_result)
            logger.info(
                "extraction_completed",
                extra={"document_id": str(document.id), "field_count": len(fields)},
            )

            self._set_status(db, document, ProcessingStatus.VALIDATING)
            issues, project = self._calculate_validation(db, document, classification, fields)

            canonical_result = CanonicalDocumentResult.compose(
                document_id=document.id,
                document_type=classification.predicted_type,
                classification_confidence=classification.confidence_score,
                extracted_fields=fields,
                processing_status=ProcessingStatus.COMPLETED,
            )
            self._persist_success(
                db,
                document,
                source_result,
                classification,
                fields,
                issues,
                project,
            )
            logger.info(
                "document_processing_completed",
                extra={
                    "document_id": str(document.id),
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "document_type": str(document.document_type),
                    "missing_expected_fields": canonical_result.missing_expected_fields,
                },
            )
            return document
        except OCRProviderError as exc:
            db.rollback()
            logger.warning(
                "document_processing_failed",
                extra={"document_id": str(document.id), "error_code": str(exc.code)},
            )
            self._fail(db, document, exc.code, PROCESSING_ERROR_MESSAGES[exc.code])
            return document
        except Exception:
            db.rollback()
            logger.exception("document_processing_failed", extra={"document_id": str(document.id)})
            self._fail(
                db,
                document,
                ProcessingErrorCode.PROCESSING_FAILED,
                PROCESSING_ERROR_MESSAGES[ProcessingErrorCode.PROCESSING_FAILED],
            )
            return document

    def _set_status(self, db: Session, document: Document, status: ProcessingStatus) -> None:
        document.processing_status = status
        db.commit()

    async def _obtain_source(self, db: Session, document: Document) -> OCRDocumentResult:
        path = self.storage.path_for(document.storage_key)
        direct_pages = None
        if document.mime_type == "application/pdf":
            pdf_result = self.pdf.extract_text(path)
            if pdf_result.has_meaningful_text:
                direct_pages = pdf_result.pages

        if direct_pages is not None:
            provider_name = "direct_pdf_text"
            pages = direct_pages
            source_path = "embedded_text"
        else:
            self._set_status(db, document, ProcessingStatus.OCR_PROCESSING)
            pages = await get_ocr_provider(self.settings).extract_document(
                path, document.mime_type, document.original_filename
            )
            provider_name = (
                str(pages[0].metadata.get("provider") or self.settings.ocr_provider)
                if pages
                else self.settings.ocr_provider
            )
            source_path = "ocr"

        result = OCRDocumentResult(
            provider=provider_name,
            pages=pages,
            assembled_text=assemble_document_text(pages),
        )
        self._set_status(db, document, ProcessingStatus.OCR_COMPLETED)
        logger.info(
            "document_source_selected",
            extra={
                "document_id": str(document.id),
                "source_path": source_path,
                "provider": provider_name,
                "page_count": result.page_count,
            },
        )
        return result

    def _calculate_validation(
        self,
        db: Session,
        document: Document,
        classification: ClassificationResult,
        fields: list[ExtractedValue],
    ) -> tuple[list[ValidationIssue], Project | None]:
        submission = db.get(Submission, document.submission_id)
        project = db.get(Project, submission.project_id) if submission else None
        duplicate = bool(
            db.scalar(
                select(Document.id)
                .where(
                    Document.submission_id == document.submission_id,
                    Document.checksum_sha256 == document.checksum_sha256,
                    Document.id != document.id,
                )
                .limit(1)
            )
        )
        configured_rules = self._load_configured_rules(
            db, project, classification.predicted_type.value
        )
        issues = self.validator.validate_document(
            None,
            classification.predicted_type,
            fields,
            project.applicant_name if project else None,
            project.company_name if project else None,
            duplicate,
            configured_rules,
        )
        logger.info(
            "validation_completed",
            extra={
                "document_id": str(document.id),
                "validation_status": str(self.validator.overall_status(issues)),
                "issue_count": len(issues),
            },
        )
        return issues, project

    def _persist_success(
        self,
        db: Session,
        document: Document,
        source_result: OCRDocumentResult,
        classification: ClassificationResult,
        fields: list[ExtractedValue],
        issues: list[ValidationIssue],
        project: Project | None,
    ) -> None:
        self._delete_derived_rows(db, document.id)
        for page in source_result.pages:
            db.add(
                OCRResult(
                    document_id=document.id,
                    provider=source_result.provider,
                    page_number=page.page_number,
                    normalized_text=page.text,
                    lines=[asdict(line) for line in page.lines],
                    metadata_json=page.metadata,
                    confidence=page.confidence,
                    duration_ms=page.duration_ms,
                )
            )
        for field in fields:
            db.add(
                ExtractedField(
                    document_id=document.id,
                    field_name=field.field_name,
                    raw_value=field.raw_value,
                    normalized_value=field.normalized_value,
                    confidence=field.confidence,
                    needs_review=field.needs_review,
                    extraction_method=field.extraction_method,
                    source_text=field.source_text,
                    evidence=(
                        [item.to_dict() for item in field.evidence] if field.evidence else None
                    ),
                )
            )
        for issue in issues:
            db.add(
                ValidationResult(
                    document_id=document.id,
                    project_id=project.id if project else None,
                    rule_type=issue.rule_type,
                    passed=issue.passed,
                    severity=issue.severity,
                    expected_value=str(issue.expected_value) if issue.expected_value else None,
                    actual_value=str(issue.actual_value) if issue.actual_value else None,
                    message=issue.message,
                    code=issue.code,
                )
            )

        document.document_type = classification.predicted_type
        document.classification_confidence = classification.confidence_score
        document.classification_meta = {
            "score": classification.score,
            "evidence": classification.evidence,
            "needs_review": classification.needs_review,
            "classifier_version": classification.classifier_version,
            "alternatives": [
                {"document_type": str(alt.document_type), "score": alt.score}
                for alt in classification.alternatives
            ],
        }
        document.error_code = None
        document.error_message = None
        document.processing_status = ProcessingStatus.COMPLETED
        db.commit()
        db.refresh(document)

    def _fail(
        self, db: Session, document: Document, code: ProcessingErrorCode, message: str
    ) -> None:
        self._delete_derived_rows(db, document.id)
        document.document_type = DocumentType.UNKNOWN
        document.classification_confidence = None
        document.classification_meta = None
        document.processing_status = ProcessingStatus.FAILED
        document.error_code = code
        document.error_message = message
        db.commit()
        db.refresh(document)

    def _delete_derived_rows(self, db: Session, document_id: uuid.UUID) -> None:
        for model in (OCRResult, ExtractedField, ValidationResult):
            db.execute(delete(model).where(model.document_id == document_id))

    def _load_configured_rules(
        self, db: Session, project: Project | None, document_type: str
    ) -> list[ConfiguredRule] | None:
        if project is None or project.checklist_id is None:
            return None
        requirement = db.scalar(
            select(DocumentRequirement).where(
                DocumentRequirement.checklist_id == project.checklist_id,
                DocumentRequirement.document_type == document_type,
            )
        )
        if requirement is None:
            return None
        rows = db.scalars(
            select(ValidationRule).where(ValidationRule.requirement_id == requirement.id)
        ).all()
        return [
            ConfiguredRule(RuleType(row.rule_type), Severity(row.severity), row.params or {})
            for row in rows
        ]
