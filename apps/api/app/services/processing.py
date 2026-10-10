import logging
import re
import time
import uuid
from dataclasses import asdict, replace

from sqlalchemy import delete, or_, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.domain import DocumentType, ProcessingStatus, RuleType, Severity
from app.core.errors import PROCESSING_ERROR_MESSAGES, ProcessingErrorCode
from app.document_intelligence.auto_acceptance import (
    SECOND_PASS_FIELDS,
    STRATEGY_FEATURES,
    parse_second_pass,
    parse_strategy,
)
from app.document_intelligence.classification.classifier import (
    ClassificationResult,
    DocumentClassifier,
)
from app.document_intelligence.classification.title_gate import assess_title
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.models import (
    OCRDocumentResult,
    OCRPage,
    OCRProviderError,
    RegionRequest,
)
from app.document_intelligence.ocr.providers import get_ocr_provider
from app.document_intelligence.ocr.text_assembly import (
    assemble_document_text,
    assemble_page_text,
)
from app.document_intelligence.preprocessing.processor import PdfProcessor, is_meaningful_text
from app.document_intelligence.preprocessing.text_layer import audit_text_layer
from app.document_intelligence.results import CanonicalDocumentResult
from app.document_intelligence.validation.engine import (
    ValidationEngine,
    ValidationIssue,
)
from app.models.entities import (
    Document,
    ExtractedField,
    OCRResult,
    Project,
    ValidationResult,
)
from app.services.consistency import lock_document_project
from app.services.document_validation import (
    policy_gated_fields,
    text_layer_mismatch_issue,
    validate_effective_document,
)
from app.services.reviews import invalidate_document_reviews
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


def _value_evidence(item: ExtractedValue):  # type: ignore[no-untyped-def]
    """The evidence box that actually holds the value (not the label box)."""
    value = item.normalized_value or ""
    digits = re.sub(r"\D", "", value)
    boxed = [entry for entry in (item.evidence or []) if entry.bounding_box is not None]
    for entry in boxed:
        source_digits = re.sub(r"\D", "", entry.source_text)
        if value in entry.source_text or (digits and digits in source_digits):
            return entry
    return boxed[-1] if boxed else None


class DocumentProcessingService:
    """The single authoritative orchestration path for a stored document.

    Algorithms remain in ``document_intelligence``. This service chooses the
    source path, coordinates each stage, and atomically replaces all derived
    persistence on success. Failed attempts retain the last successful generation
    and review history; FAILED makes its operational state explicit and prevents
    use in a current submission decision.
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
        lock_document_project(db, document)
        db.refresh(document)
        if document.processing_status in _ACTIVE_STATUSES:
            db.commit()
            return document

        started = time.perf_counter()
        claimed_document_id = db.scalar(
            update(Document)
            .where(
                Document.id == document.id,
                or_(
                    Document.processing_status.is_(None),
                    Document.processing_status.not_in(
                        [status.value for status in _ACTIVE_STATUSES]
                    ),
                ),
            )
            .values(
                processing_status=ProcessingStatus.PREPROCESSING,
                error_code=None,
                error_message=None,
            )
            .returning(Document.id)
        )
        if claimed_document_id is None:
            db.commit()
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

            extraction_source = source_result
            if source_result.page_count > 1:
                split = self._split_multi_document(source_result)
                if split is not None:
                    classification, extraction_source = split

            classification = self._apply_title_gate(source_result, classification)

            self._set_status(db, document, ProcessingStatus.EXTRACTING)
            fields = self.extractor.extract(classification.predicted_type, extraction_source)
            await self._second_pass(document, source_result, fields)
            logger.info(
                "extraction_completed",
                extra={"document_id": str(document.id), "field_count": len(fields)},
            )

            self._set_status(db, document, ProcessingStatus.VALIDATING)
            issues, project = self._calculate_validation(db, document, classification, fields)
            if classification.multiple_documents_in_file and not any(
                item.code == "MULTIPLE_DOCUMENTS_IN_FILE" for item in issues
            ):
                issues.append(
                    ValidationIssue(
                        RuleType.EXPECTED_DOCUMENT_TYPE,
                        False,
                        Severity.WARNING,
                        None,
                        None,
                        "한 파일에 서로 다른 종류의 서류가 들어 있어 확인이 필요합니다.",
                        "MULTIPLE_DOCUMENTS_IN_FILE",
                    )
                )

            if source_result.text_layer and source_result.text_layer.get("mismatch"):
                issues.append(text_layer_mismatch_issue())

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
            # Provider/decoder exception strings can contain document text or paths.
            logger.error("document_processing_failed", extra={"document_id": str(document.id)})
            self._fail(
                db,
                document,
                ProcessingErrorCode.PROCESSING_FAILED,
                PROCESSING_ERROR_MESSAGES[ProcessingErrorCode.PROCESSING_FAILED],
            )
            return document

    async def _second_pass(
        self, document: Document, source_result: OCRDocumentResult, fields: list[ExtractedValue]
    ) -> None:
        """Re-read the region of each OCR-read numeric/date field with different preprocessing
        and store the reading with the page (see auto_acceptance.py). Best effort: a failed
        second pass only means no corroboration from it."""
        if not STRATEGY_FEATURES[parse_strategy(self.settings.auto_accept_strategy)].second_pass:
            return
        requests = []
        for item in fields:
            if (
                item.field_name not in SECOND_PASS_FIELDS
                or item.normalized_value is None
                or item.needs_review
                or not item.evidence
                or not any(entry.source_kind == "ocr" for entry in item.evidence)
            ):
                continue
            evidence = _value_evidence(item)
            if evidence is not None and evidence.bounding_box is not None:
                requests.append(
                    RegionRequest(item.field_name, evidence.page_number, evidence.bounding_box)
                )
        if not requests:
            return
        try:
            from app.services.storage.local import detected_mime

            path = self.storage.path_for(document.storage_key)
            readings = await get_ocr_provider(self.settings).read_regions(
                path, detected_mime(path), requests
            )
        except Exception:
            logger.warning("second_pass_failed", extra={"document_id": str(document.id)})
            return
        values = {item.field_name: item.normalized_value for item in fields}
        pages = {page.page_number: page for page in source_result.pages}
        for reading in readings:
            page = pages.get(reading.page_number)
            if page is None:
                continue
            page.metadata.setdefault("second_pass", {})[reading.field_name] = {
                "text": reading.text,
                "normalized": parse_second_pass(reading.field_name, reading.text),
                "confidence": reading.confidence,
                "preprocess": reading.preprocess,
                "first_pass_value": values.get(reading.field_name),
            }

    def _apply_title_gate(
        self, source_result: OCRDocumentResult, classification: ClassificationResult
    ) -> ClassificationResult:
        """OCR-read documents must prove their type before any field can be auto-accepted
        (see classification/title_gate.py). Embedded PDF text is exact and is not gated."""
        if classification.predicted_type == DocumentType.UNKNOWN:
            return classification
        ocr_pages = [
            page for page in source_result.pages if page.metadata.get("source") != "direct_pdf_text"
        ]
        if not ocr_pages:
            return classification
        assessment = assess_title(ocr_pages, classification.predicted_type, classification.evidence)
        gated = replace(classification, title_gate=assessment.to_dict())
        if assessment.near_match:
            return replace(
                gated,
                predicted_type=DocumentType.UNKNOWN,
                confidence_score=0.0,
                score=0.0,
                evidence=[],
                needs_review=True,
            )
        if not assessment.established:
            return replace(gated, needs_review=True)
        return gated

    def _split_multi_document(
        self, source_result: OCRDocumentResult
    ) -> tuple[ClassificationResult, OCRDocumentResult] | None:
        """Classify each page. When pages of one file are different *supported* types
        (e.g. a 사업자등록증 followed by a 납세증명서), flag the file and extract only from
        the pages of the first type, so fields from different documents are never merged.
        Unclassifiable pages (an unrelated page, a blank page) are ignored."""
        page_types: dict[int, DocumentType] = {}
        for page in source_result.pages:
            if is_meaningful_text(page.text):
                page_types[page.page_number] = self.classifier.classify(page.text).predicted_type
        supported = {item for item in page_types.values() if item != DocumentType.UNKNOWN}
        if len(supported) < 2:
            return None
        first = next(item for _, item in sorted(page_types.items()) if item != DocumentType.UNKNOWN)
        pages = [page for page in source_result.pages if page_types.get(page.page_number) == first]
        restricted = OCRDocumentResult(
            provider=source_result.provider,
            pages=pages,
            assembled_text=assemble_document_text(pages),
        )
        return (
            ClassificationResult(
                predicted_type=first,
                confidence_score=0.0,
                score=0.0,
                evidence=[],
                needs_review=True,
                multiple_documents_in_file=True,
                page_types={str(number): str(item) for number, item in sorted(page_types.items())},
            ),
            restricted,
        )

    def _set_status(self, db: Session, document: Document, status: ProcessingStatus) -> None:
        document.processing_status = status
        db.commit()

    async def _obtain_source(self, db: Session, document: Document) -> OCRDocumentResult:
        """Choose the source per page, not per document.

        A single document-level gate is wrong for mixed PDFs: one page with
        a real text layer made the whole document skip OCR, so every scanned
        page in the same file silently contributed nothing. Verified on a
        2-page PDF whose first page had a text layer and whose second page
        was a real scan -- the scan page yielded 0 characters and every field
        on it was lost.
        """
        import asyncio

        from app.services.storage.local import detected_mime

        path = self.storage.path_for(document.storage_key)
        mime_type = detected_mime(path)
        is_pdf = mime_type == "application/pdf"
        embedded_pages: list[OCRPage] = []
        provenance: dict = {}
        if is_pdf:
            pdf_result = await asyncio.to_thread(self.pdf.extract_text, path)
            embedded_pages = pdf_result.pages
            provenance = pdf_result.provenance
            if not embedded_pages:
                raise OCRProviderError(ProcessingErrorCode.OCR_EMPTY_RESULT)

        # Prefer a real text layer page by page: it carries exact characters
        # and no recognition error. Only pages without a usable layer are
        # handed to OCR.
        # A page whose text layer cannot be trusted (hidden text carrying dates or numbers,
        # unreadable font encoding, pictures, overlapping text) is read from its pixels instead.
        usable_by_page = {
            page.page_number: page
            for page in embedded_pages
            if is_meaningful_text(page.text) and page.metadata["text_layer"]["trusted"]
        }
        needs_ocr = [
            page.page_number for page in embedded_pages if page.page_number not in usable_by_page
        ]
        if not is_pdf:
            # A PNG/JPEG upload has no PDF page grid to enumerate, so it never
            # appears in `embedded_pages` and the loop above cannot produce a
            # single page for it. Enumerating candidates *from the text layer
            # alone* therefore skipped OCR for every image: the document
            # finished COMPLETED with zero characters, an UNKNOWN type and no
            # fields, while looking like it had succeeded. A non-PDF upload is
            # exactly one page, and that page can only be read by OCR.
            needs_ocr = [1]

        pages = list(usable_by_page.values())
        source_path = "embedded_text"
        provider_name = "direct_pdf_text"

        if needs_ocr:
            self._set_status(db, document, ProcessingStatus.OCR_PROCESSING)
            ocr_pages = await get_ocr_provider(self.settings).extract_document(
                path, mime_type, document.original_filename
            )
            by_page = {page.page_number: page for page in ocr_pages}
            if len(by_page) != len(ocr_pages) or any(number not in by_page for number in needs_ocr):
                raise OCRProviderError(ProcessingErrorCode.OCR_INVALID_RESPONSE)
            for page_number in needs_ocr:
                ocr_page = by_page.get(page_number)
                if ocr_page is not None:
                    if ocr_page.lines:
                        # derive the text from the lines with the current reading order
                        ocr_page.text = assemble_page_text(ocr_page.lines)
                    pages.append(ocr_page)
            provider_name = str(
                next(
                    (
                        page.metadata.get("provider")
                        for page in ocr_pages
                        if page.metadata.get("provider")
                    ),
                    self.settings.ocr_provider,
                )
            )
            source_path = "mixed" if pages[: len(usable_by_page)] else "ocr"

        pages.sort(key=lambda page: page.page_number)
        for page in pages:
            # A mixed document now has pages from two different sources, so
            # each OCRResult row must record its own provenance rather than
            # inheriting one document-level provider string.
            if page.metadata.get("source") != "direct_pdf_text":
                page.metadata.setdefault("source", "ocr")

        result = OCRDocumentResult(
            provider=provider_name,
            pages=pages,
            assembled_text=assemble_document_text(pages),
            text_layer=audit_text_layer(embedded_pages, pages, provenance) if is_pdf else None,
        )
        if not result.pages or not result.assembled_text.strip():
            raise OCRProviderError(ProcessingErrorCode.OCR_EMPTY_RESULT)
        expected_pages = len(embedded_pages) if is_pdf else 1
        if result.page_count != expected_pages:
            raise OCRProviderError(ProcessingErrorCode.OCR_INVALID_RESPONSE)
        self._set_status(db, document, ProcessingStatus.OCR_COMPLETED)
        logger.info(
            "document_source_selected",
            extra={
                "document_id": str(document.id),
                "source_path": source_path,
                "provider": provider_name,
                "page_count": result.page_count,
                "page_sources": [
                    "embedded_pdf_text"
                    if page.metadata.get("source") == "direct_pdf_text"
                    else "ocr"
                    for page in pages
                ],
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
        issues, project = validate_effective_document(
            db, document, classification.predicted_type, policy_gated_fields(fields)
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
        lock_document_project(db, document)
        db.refresh(document)
        invalidate_document_project_verification(db, document)
        invalidate_document_reviews(db, document.id)
        self._delete_derived_rows(db, document.id)
        for page in source_result.pages:
            page_provider = (
                "direct_pdf_text"
                if page.metadata.get("source") == "direct_pdf_text"
                else source_result.provider
            )
            db.add(
                OCRResult(
                    document_id=document.id,
                    provider=page_provider,
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
            "multiple_documents_in_file": classification.multiple_documents_in_file,
            "page_types": classification.page_types,
            "title_gate": classification.title_gate,
            "text_layer": source_result.text_layer,
            "alternatives": [
                {"document_type": str(alt.document_type), "score": alt.score}
                for alt in classification.alternatives
            ],
        }
        document.error_code = None
        document.error_message = None
        document.processing_status = ProcessingStatus.COMPLETED
        document.processing_version += 1
        db.commit()
        db.refresh(document)

    def _fail(
        self, db: Session, document: Document, code: ProcessingErrorCode, message: str
    ) -> None:
        lock_document_project(db, document)
        db.refresh(document)
        invalidate_document_project_verification(db, document)
        document.processing_status = ProcessingStatus.FAILED
        document.error_code = code
        document.error_message = message
        db.commit()
        db.refresh(document)

    def _delete_derived_rows(self, db: Session, document_id: uuid.UUID) -> None:
        for model in (OCRResult, ExtractedField, ValidationResult):
            statement = delete(model).where(model.document_id == document_id)
            if model is ValidationResult:
                statement = statement.where(or_(model.scope.is_(None), model.scope != "SUBMISSION"))
            db.execute(statement)
