import pytest
from PIL import Image

from app.core.config import Settings
from app.core.domain import Severity
from app.core.errors import ProcessingErrorCode
from app.document_intelligence.ocr.models import OCRProviderError
from app.document_intelligence.ocr.providers import (
    MockOCRProvider,
    PaddleOCRProvider,
    get_ocr_provider,
)


def make_settings(**overrides: object) -> Settings:
    values = {
        "ocr_provider": "paddle",
        "paddle_ocr_device": "cpu",
        "paddle_ocr_lang": "korean",
        "paddle_ocr_rec_model_name": "korean_PP-OCRv5_mobile_rec",
        "paddle_ocr_det_model_name": "PP-OCRv5_mobile_det",
        **overrides,
    }
    return Settings(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_mock_provider_selects_fixture_by_filename(tmp_path) -> None:
    path = tmp_path / "career_sample.png"
    Image.new("RGB", (200, 200), "white").save(path)
    pages = await MockOCRProvider().extract_document(path, "image/png")
    assert "경력증명서" in pages[0].text
    assert pages[0].metadata["provider"] == "mock"


@pytest.mark.asyncio
async def test_mock_provider_defaults_to_graduation(tmp_path) -> None:
    path = tmp_path / "scan001.png"
    Image.new("RGB", (200, 200), "white").save(path)
    pages = await MockOCRProvider().extract_document(path, "image/png")
    assert "졸업증명서" in pages[0].text


@pytest.mark.asyncio
async def test_mock_provider_empty_fixture_is_empty_text(tmp_path) -> None:
    path = tmp_path / "empty_scan.png"
    Image.new("RGB", (200, 200), "white").save(path)
    pages = await MockOCRProvider().extract_document(path, "image/png")
    assert pages[0].text == ""


def test_provider_selection_supports_mock_and_paddle() -> None:
    assert isinstance(get_ocr_provider(make_settings(ocr_provider="mock")), MockOCRProvider)
    assert isinstance(get_ocr_provider(make_settings(ocr_provider="paddle")), PaddleOCRProvider)


def test_provider_selection_reuses_real_provider_instance() -> None:
    settings = make_settings(ocr_provider="paddle")
    assert get_ocr_provider(settings) is get_ocr_provider(settings)


def test_provider_selection_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported OCR_PROVIDER"):
        get_ocr_provider(make_settings(ocr_provider="unknown"))


@pytest.mark.asyncio
async def test_paddle_normalizes_tuple_output_without_leaking_raw_shape(tmp_path) -> None:
    path = tmp_path / "business.png"
    Image.new("RGB", (200, 200), "white").save(path)
    provider = PaddleOCRProvider(make_settings())
    provider.__dict__["_engine"] = _FakePaddleEngine(
        [
            [
                ([[0, 0], [100, 0], [100, 20], [0, 20]], ("사업자등록증", 0.97)),
                ([[0, 30], [160, 30], [160, 50], [0, 50]], ("사업자등록번호 123-45-67891", 0.94)),
            ]
        ]
    )

    pages = await provider.extract_document(path, "image/png")

    assert pages[0].text == "사업자등록증\n사업자등록번호 123-45-67891"
    assert pages[0].confidence == pytest.approx(0.955)
    assert pages[0].metadata["provider"] == "paddle"
    assert pages[0].metadata["rec_model_name"] == "korean_PP-OCRv5_mobile_rec"
    assert "rec_texts" not in pages[0].metadata
    assert pages[0].lines[1].bounding_box is not None


@pytest.mark.asyncio
async def test_paddle_normalizes_ppocr_v3_dict_output(tmp_path) -> None:
    path = tmp_path / "graduation.png"
    Image.new("RGB", (200, 200), "white").save(path)
    provider = PaddleOCRProvider(make_settings())
    provider.__dict__["_engine"] = _FakePaddleEngine(
        [
            {
                "rec_texts": ["졸업증명서", "성명 홍길동"],
                "rec_scores": [0.98, 0.96],
                "rec_polys": [
                    [[0, 0], [100, 0], [100, 20], [0, 20]],
                    [[0, 30], [100, 30], [100, 50], [0, 50]],
                ],
            }
        ]
    )

    pages = await provider.extract_document(path, "image/png")

    assert pages[0].text == "졸업증명서\n성명 홍길동"
    assert all(line.bounding_box is not None for line in pages[0].lines)


@pytest.mark.asyncio
async def test_paddle_empty_result_raises(tmp_path) -> None:
    path = tmp_path / "empty.png"
    Image.new("RGB", (200, 200), "white").save(path)
    provider = PaddleOCRProvider(make_settings())
    provider.__dict__["_engine"] = _FakePaddleEngine([[]])

    with pytest.raises(OCRProviderError) as exc_info:
        await provider.extract_document(path, "image/png")

    assert exc_info.value.code == ProcessingErrorCode.OCR_EMPTY_RESULT


@pytest.mark.asyncio
async def test_paddle_fixture_flows_through_classifier_extractor_validator(tmp_path) -> None:
    from app.core.domain import DocumentType
    from app.document_intelligence.classification.classifier import DocumentClassifier
    from app.document_intelligence.extraction.registry import ExtractorRegistry
    from app.document_intelligence.validation.engine import ValidationEngine

    path = tmp_path / "business.png"
    Image.new("RGB", (200, 200), "white").save(path)
    provider = PaddleOCRProvider(make_settings())
    provider.__dict__["_engine"] = _FakePaddleEngine(
        [
            [
                ([[0, 0], [100, 0], [100, 20], [0, 20]], ("사업자등록증", 0.99)),
                ([[0, 30], [140, 30], [140, 50], [0, 50]], ("상호 한국테크", 0.99)),
                ([[0, 60], [140, 60], [140, 80], [0, 80]], ("대표자 이영희", 0.99)),
                (
                    [[0, 90], [220, 90], [220, 110], [0, 110]],
                    ("사업자등록번호 123-45-67891", 0.99),
                ),
            ]
        ]
    )

    text = (await provider.extract_document(path, "image/png"))[0].text
    classification = DocumentClassifier().classify(text)
    extracted = ExtractorRegistry().extract(classification.predicted_type, text)
    issues = ValidationEngine().validate_document(
        None,
        DocumentType(classification.predicted_type),
        extracted,
        None,
        None,
        False,
        None,
    )

    assert classification.predicted_type == DocumentType.BUSINESS_REGISTRATION_CERTIFICATE
    assert {field.field_name for field in extracted} >= {
        "company_name",
        "representative_name",
        "business_registration_number",
    }
    # This fixture prints only four rows, so the remaining fields the
    # 사업자등록증 extractor declares are genuinely absent and the missing-field
    # net fires. Both identity fields it does resolve must stay unflagged.
    assert issues
    flagged = {issue.expected_value for issue in issues}
    assert "company_name" not in flagged
    assert "business_registration_number" not in flagged


@pytest.mark.asyncio
async def test_unresolved_expected_field_is_flagged_even_with_no_configured_rules(
    tmp_path,
) -> None:
    """The safety net must fire for a document that is missing a field its
    type actually requires, with or without a checklist behind it."""
    from app.core.domain import DocumentType
    from app.document_intelligence.extraction.registry import ExtractorRegistry
    from app.document_intelligence.validation.engine import ValidationEngine

    # A 사업자등록증 with no 사업자등록번호 anywhere: company_name resolves,
    # the identifier does not.
    fields = ExtractorRegistry().extract(
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, "사업자등록증\n상호 한국테크"
    )
    issues = ValidationEngine().validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        fields,
        None,
        None,
        False,
        None,
    )
    assert "business_registration_number" in {issue.expected_value for issue in issues}
    assert "company_name" not in {issue.expected_value for issue in issues}
    assert {issue.code for issue in issues} == {"MISSING_REQUIRED_FIELD"}
    assert all(not issue.passed for issue in issues)
    # WARNING severity, so an unresolved field routes to review rather than
    # becoming a deterministic correction demand.
    assert all(issue.severity == Severity.WARNING for issue in issues)


@pytest.mark.asyncio
async def test_paddle_pdf_render_directory_is_removed_after_processing(
    tmp_path, monkeypatch
) -> None:
    import fitz

    path = tmp_path / "two_pages.pdf"
    pdf = fitz.open()
    pdf.new_page()
    pdf.new_page()
    pdf.save(path)
    pdf.close()
    rendered_dir = tmp_path / "advs_paddle_controlled"

    def controlled_mkdtemp(suffix=None, prefix=None, dir=None) -> str:
        rendered_dir.mkdir()
        return str(rendered_dir)

    monkeypatch.setattr(
        "app.document_intelligence.ocr.providers.tempfile.mkdtemp",
        controlled_mkdtemp,
    )
    provider = PaddleOCRProvider(make_settings())
    provider.__dict__["_engine"] = _FakePaddleEngine(
        [[([[0, 0], [100, 0], [100, 20], [0, 20]], ("사업자등록증", 0.99))]]
    )

    pages = await provider.extract_document(path, "application/pdf")

    assert len(pages) == 2
    assert not rendered_dir.exists()


class _FakePaddleEngine:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def predict(self, path: str) -> object:
        return self.payload
