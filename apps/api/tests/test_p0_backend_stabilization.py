import io
import logging
import math
import tempfile
import uuid
from datetime import date
from pathlib import Path

import fitz

from app.core.config import Settings
from app.core.domain import (
    EXPECTED_FIELDS,
    REVIEWABLE_FIELDS,
    DocumentType,
    ProcessingStatus,
    RuleOperator,
    RuleType,
    Severity,
)
from app.core.logging import configure_logging
from app.document_intelligence.extraction.base import BaseDocumentExtractor, candidate_after_label
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.providers import PaddleOCRProvider
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    RequirementSnapshot,
    SubmissionRule,
    SubmissionVerificationEngine,
    VerificationContext,
)
from app.services.storage.local import LocalStorageService


class ProbeExtractor(BaseDocumentExtractor):
    document_type = DocumentType.ENROLLMENT_CERTIFICATE

    def extract(self, text):
        return []


def test_issue_date_footer_label_does_not_suppress_valid_bare_issue_date() -> None:
    field = ProbeExtractor().issue_date_field(
        "재학증명서\n2026년 1월 10일\n가나다대학교 총장\n인터넷 발급일로부터 90일간 원본대조 가능",
        ["발급일자", "발급일", "발행일자"],
    )

    assert field.normalized_value == "2026-01-10"
    assert field.extraction_method == "document_semantic_issue_date"
    assert field.needs_review


def test_issue_date_ambiguous_bare_dates_still_abstain() -> None:
    field = ProbeExtractor().issue_date_field(
        "재학증명서\n2026년 1월 10일\n2026년 1월 11일\n가나다대학교 총장",
        ["발급일자", "발급일", "발행일자"],
    )

    assert field.normalized_value is None


def test_compound_label_matching_is_independent_of_alias_order() -> None:
    text = "사업자등록증\n대표자 성명 김민수\n법인명칭 주식회사 예시산업"

    representative_short_first = candidate_after_label(
        text, ["대표자", "대표자 성명"], "representative_name"
    )
    representative_compound_first = candidate_after_label(
        text, ["대표자 성명", "대표자"], "representative_name"
    )
    company_short_first = candidate_after_label(text, ["법인명", "법인명칭"], "company_name")
    company_compound_first = candidate_after_label(text, ["법인명칭", "법인명"], "company_name")

    assert representative_short_first is not None
    assert representative_compound_first is not None
    assert representative_short_first.value == representative_compound_first.value == "김민수"
    assert company_short_first is not None
    assert company_compound_first is not None
    assert company_short_first.value == company_compound_first.value == "주식회사 예시산업"


def _field(name: str, value: str | None) -> FieldSnapshot:
    return FieldSnapshot(uuid.uuid4(), name, value, False, value is not None)


def _document(document_type: DocumentType, fields: dict[str, str]) -> DocumentSnapshot:
    return DocumentSnapshot(
        uuid.uuid4(),
        document_type,
        ProcessingStatus.COMPLETED,
        uuid.uuid4().hex,
        {name: _field(name, value) for name, value in fields.items()},
    )


def test_company_comparison_allows_safe_spacing_variation() -> None:
    rule = SubmissionRule(
        uuid.uuid4(),
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value,
            "source_field": "company_name",
            "target_document_type": DocumentType.SME_CONFIRMATION_CERTIFICATE.value,
            "target_field": "company_name",
            "operator": RuleOperator.EQUALS.value,
            "value_type": "string",
        },
    )
    result = SubmissionVerificationEngine().verify(
        project_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        requirements=[
            RequirementSnapshot(uuid.uuid4(), DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, True),
            RequirementSnapshot(
                uuid.uuid4(), DocumentType.SME_CONFIRMATION_CERTIFICATE, True, (rule,)
            ),
        ],
        documents=[
            _document(
                DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
                {
                    "company_name": "주식회사 플래시21",
                    "business_registration_number": "0000000000",
                },
            ),
            _document(
                DocumentType.SME_CONFIRMATION_CERTIFICATE,
                {
                    "company_name": "주식회사플래시21",
                    "business_registration_number": "0000000000",
                    "valid_from": "2026-01-01",
                    "valid_until": "2027-01-01",
                },
            ),
        ],
        context=VerificationContext(date(2026, 1, 2)),
    )

    comparison = next(item for item in result.rule_results if item.rule_id == rule.id)
    assert comparison.outcome.value == "PASS"


def test_upload_validation_accepts_large_valid_pdf_points_within_page_limit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "legitimate_form.pdf"
        doc = fitz.open()
        doc.new_page(width=1117, height=1408)
        doc.save(path)
        doc.close()

        service = LocalStorageService(Settings(storage_path=Path(tmp) / "store"))

        service._validate_decodable(path, ".pdf")


def test_extractor_supported_fields_are_reviewable_without_becoming_default_required() -> None:
    text = (
        "사업자등록증\n"
        "상호 한국테크\n"
        "대표자 이영희\n"
        "사업자등록번호 123-45-67890\n"
        "사업장 소재지 서울특별시 강남구\n"
        "업태 서비스업\n"
        "종목 소프트웨어 개발\n"
        "발급일자 2026-01-10"
    )

    extracted = {
        field.field_name
        for field in ExtractorRegistry().extract(
            DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, text
        )
    }

    assert extracted <= set(REVIEWABLE_FIELDS[DocumentType.BUSINESS_REGISTRATION_CERTIFICATE])
    assert "business_address" in REVIEWABLE_FIELDS[DocumentType.BUSINESS_REGISTRATION_CERTIFICATE]
    assert "business_address" not in EXPECTED_FIELDS[DocumentType.BUSINESS_REGISTRATION_CERTIFICATE]


def test_application_logging_survives_root_logger_level_change() -> None:
    configure_logging("INFO")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    app_logger = logging.getLogger("app")
    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger("app.document_intelligence.ocr").info("page processed")

    assert "page processed" in stream.getvalue()


def _pdf_with_page_box_and_raster(
    directory: Path, page_points: tuple[float, float], raster_px: tuple[int, int]
) -> Path:
    """A PDF whose page box deliberately overstates its embedded raster."""
    path = directory / "oversized_page.pdf"
    page_width, page_height = page_points
    raster_width, raster_height = raster_px
    document = fitz.open()
    page = document.new_page(width=page_width, height=page_height)
    image = fitz.Pixmap(
        fitz.csGRAY,
        fitz.IRect(0, 0, raster_width, raster_height),
        False,
    )
    image.set_rect(image.irect, (255, 255, 255))
    page.insert_image(page.rect, pixmap=image)
    document.save(path)
    document.close()
    return path


def test_oversized_page_box_is_rendered_at_its_own_resolution_not_rejected() -> None:
    """F-01 follow-up: the raster budget must not reject a real document.

    The page box is ~3x A4 and carries a 72 DPI scan. Projecting the configured
    render DPI onto the box exceeds the per-page pixel budget by a fraction of
    a percent and rejected the document outright, even though the pre-P0
    pipeline processed it. The budget bounds decode cost, so the page must
    render at the resolution it actually carries.
    """
    settings = Settings(ocr_provider="paddle")
    provider = PaddleOCRProvider(settings)

    with tempfile.TemporaryDirectory() as directory:
        path = _pdf_with_page_box_and_raster(Path(directory), (1117.0, 1408.0), (1117, 1408))
        with fitz.open(path) as document:
            page = document[0]
            configured = math.ceil(page.rect.width * provider.render_scale) * math.ceil(
                page.rect.height * provider.render_scale
            )
            scale, reason = provider._page_render_scale(page)
            fitted = math.ceil(page.rect.width * scale) * math.ceil(page.rect.height * scale)

    assert configured > settings.max_image_pixels, "fixture must trip the budget at configured DPI"
    assert reason == "source_resolution_fit"
    assert fitted <= settings.max_image_pixels


def test_page_within_budget_renders_at_the_configured_dpi() -> None:
    """Fitting must not silently downscale documents that already fit."""
    provider = PaddleOCRProvider(Settings(ocr_provider="paddle"))

    with tempfile.TemporaryDirectory() as directory:
        path = _pdf_with_page_box_and_raster(Path(directory), (595.0, 842.0), (1653, 2338))
        with fitz.open(path) as document:
            scale, reason = provider._page_render_scale(document[0])

    assert scale == provider.render_scale
    assert reason == "configured_render_dpi"


def test_vector_page_is_never_downscaled_to_source_resolution() -> None:
    """A page with no embedded raster has no source resolution to fall back to."""
    provider = PaddleOCRProvider(Settings(ocr_provider="paddle"))

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "vector.pdf"
        document = fitz.open()
        document.new_page(width=1117.0, height=1408.0)
        document.save(path)
        document.close()
        with fitz.open(path) as document:
            page = document[0]
            assert provider._source_raster_scale(page) is None
            scale, reason = provider._page_render_scale(page)

    assert scale == provider.render_scale
    assert reason == "configured_render_dpi"
