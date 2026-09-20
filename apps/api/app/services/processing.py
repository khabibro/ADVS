import logging
import time
import uuid
from dataclasses import asdict

from sqlalchemy import select
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
from app.document_intelligence.ocr.models import OCRDocumentResult, OCRPage, OCRProviderError
from app.document_intelligence.ocr.providers import get_ocr_provider
from app.document_intelligence.ocr.text_assembly import assemble_document_text
from app.document_intelligence.preprocessing.processor import PdfProcessor
from app.document_intelligence.results import CanonicalDocumentResult
from app.document_intelligence.validation.engine import ConfiguredRule, ValidationEngine
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

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """Coordinates the pipeline stages; it does not implement their
    algorithms itself (those live in document_intelligence/*)."""

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
        if document.processing_status == ProcessingStatus.COMPLETED:
            return document

        started = time.perf_counter()
        logger.info("document_processing_started", extra={"document_id": str(document.id)})
        try:
            ocr_result = await self._run_ocr_stage(db, document)
            classification = self._run_classification_stage(db, document, ocr_result.assembled_text)
            fields = self._run_extraction_stage(db, document, classification, ocr_result)
            canonical_result = CanonicalDocumentResult.compose(
                document_id=document.id,
                document_type=classification.predicted_type,
                classification_confidence=classification.confidence_score,
                extracted_fields=fields,
                processing_status=ProcessingStatus.EXTRACTING,
            )
            self._run_validation_stage(db, document, fields)
            document.processing_status = ProcessingStatus.COMPLETED
            db.commit()
            db.refresh(document)
            logger.info(
                "document_processing_completed",
                extra={
                    "document_id": str(document.id),
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "document_type": document.document_type,
                    "missing_expected_fields": canonical_result.missing_expected_fields,
                },
            )
            return document
        except OCRProviderError as exc:
            logger.warning(
                "document_processing_failed",
                extra={"document_id": str(document.id), "error_code": str(exc.code)},
            )
            self._fail(db, document, exc.code, PROCESSING_ERROR_MESSAGES[exc.code])
            return document
        except Exception:
            logger.exception("document_processing_failed", extra={"document_id": str(document.id)})
            self._fail(
                db,
                document,
                ProcessingErrorCode.PROCESSING_FAILED,
                PROCESSING_ERROR_MESSAGES[ProcessingErrorCode.PROCESSING_FAILED],
            )
            return document

    def _fail(
        self, db: Session, document: Document, code: ProcessingErrorCode, message: str
    ) -> None:
        document.processing_status = ProcessingStatus.FAILED
        document.error_code = code
        document.error_message = message
        db.commit()

    async def _run_ocr_stage(self, db: Session, document: Document) -> OCRDocumentResult:
        path = self.storage.path_for(document.storage_key)
        document.processing_status = ProcessingStatus.PREPROCESSING
        db.commit()

        direct_text = ""
        if document.mime_type == "application/pdf":
            pdf_result = self.pdf.extract_text(path)
            direct_text = pdf_result.text if pdf_result.has_meaningful_text else ""

        document.processing_status = ProcessingStatus.OCR_PROCESSING
        db.commit()
        ocr_started = time.perf_counter()

        if direct_text:
            provider_name = "direct_pdf_text"
            pages: list[OCRPage] = pdf_result.pages
        else:
            pages = await get_ocr_provider(self.settings).extract_document(
                path, document.mime_type, document.original_filename
            )
            provider_name = (
                str(pages[0].metadata.get("provider") or "mock")
                if pages
                else self.settings.ocr_provider
            )

        assembled_text = assemble_document_text(pages)
        result = OCRDocumentResult(
            provider=provider_name, pages=pages, assembled_text=assembled_text
        )

        # Idempotent reprocessing: replace derived OCR rows, don't accumulate.
        for existing in list(document.ocr_results):
            db.delete(existing)
        for page in pages:
            db.add(
                OCRResult(
                    document_id=document.id,
                    provider=provider_name,
                    page_number=page.page_number,
                    normalized_text=page.text,
                    lines=[asdict(line) for line in page.lines],
                    metadata_json=page.metadata,
                    confidence=page.confidence,
                    duration_ms=page.duration_ms,
                )
            )
        document.processing_status = ProcessingStatus.OCR_COMPLETED
        db.commit()
        logger.info(
            "ocr_completed",
            extra={
                "document_id": str(document.id),
                "duration_ms": int((time.perf_counter() - ocr_started) * 1000),
                "provider": provider_name,
                "page_count": result.page_count,
            },
        )
        return result

    def _run_classification_stage(
        self, db: Session, document: Document, text: str
    ) -> ClassificationResult:
        document.processing_status = ProcessingStatus.CLASSIFYING
        db.commit()
        result = self.classifier.classify(text, document.original_filename)
        document.document_type = result.predicted_type
        document.classification_confidence = result.confidence_score
        document.classification_meta = {
            "score": result.score,
            "evidence": result.evidence,
            "needs_review": result.needs_review,
            "classifier_version": result.classifier_version,
            "alternatives": [
                {"document_type": str(alt.document_type), "score": alt.score}
                for alt in result.alternatives
            ],
        }
        db.commit()
        logger.info(
            "classification_completed",
            extra={
                "document_id": str(document.id),
                "document_type": str(result.predicted_type),
                "needs_review": result.needs_review,
            },
        )
        return result

    def _run_extraction_stage(
        self,
        db: Session,
        document: Document,
        classification: ClassificationResult,
        ocr_result: OCRDocumentResult,
    ) -> list[ExtractedValue]:
        document.processing_status = ProcessingStatus.EXTRACTING
        db.commit()
        fields = self.extractor.extract(classification.predicted_type, ocr_result)
        for existing in list(document.extracted_fields):
            db.delete(existing)
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
        db.commit()
        logger.info(
            "extraction_completed",
            extra={"document_id": str(document.id), "field_count": len(fields)},
        )
        return fields

    def _run_validation_stage(
        self, db: Session, document: Document, fields: list[ExtractedValue]
    ) -> None:
        document.processing_status = ProcessingStatus.VALIDATING
        db.commit()
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
        configured_rules = self._load_configured_rules(db, project, document.document_type)
        issues = self.validator.validate_document(
            None,
            DocumentType(document.document_type),
            fields,
            project.applicant_name if project else None,
            project.company_name if project else None,
            duplicate,
            configured_rules,
        )
        # Idempotent reprocessing: replace derived validation rows.
        for existing in list(document.validation_results):
            db.delete(existing)
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
        db.commit()
        logger.info(
            "validation_completed",
            extra={
                "document_id": str(document.id),
                "validation_status": str(self.validator.overall_status(issues)),
                "issue_count": len(issues),
            },
        )

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
