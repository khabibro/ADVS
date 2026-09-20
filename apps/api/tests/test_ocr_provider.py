import pytest

from app.core.config import Settings
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
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    pages = await MockOCRProvider().extract_document(path, "image/png")
    assert "경력증명서" in pages[0].text
    assert pages[0].metadata["provider"] == "mock"


@pytest.mark.asyncio
async def test_mock_provider_defaults_to_graduation(tmp_path) -> None:
    path = tmp_path / "scan001.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    pages = await MockOCRProvider().extract_document(path, "image/png")
    assert "졸업증명서" in pages[0].text


@pytest.mark.asyncio
async def test_mock_provider_empty_fixture_is_empty_text(tmp_path) -> None:
    path = tmp_path / "empty_scan.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
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
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    provider = PaddleOCRProvider(make_settings())
    provider.__dict__["_engine"] = _FakePaddleEngine(
        [
            [
                ([[0, 0], [100, 0], [100, 20], [0, 20]], ("사업자등록증", 0.97)),
                ([[0, 30], [160, 30], [160, 50], [0, 50]], ("사업자등록번호 123-45-67890", 0.94)),
            ]
        ]
    )

    pages = await provider.extract_document(path, "image/png")

    assert pages[0].text == "사업자등록증\n사업자등록번호 123-45-67890"
    assert pages[0].confidence == pytest.approx(0.955)
    assert pages[0].metadata["provider"] == "paddle"
    assert pages[0].metadata["rec_model_name"] == "korean_PP-OCRv5_mobile_rec"
    assert "rec_texts" not in pages[0].metadata
    assert pages[0].lines[1].bounding_box is not None


@pytest.mark.asyncio
async def test_paddle_normalizes_ppocr_v3_dict_output(tmp_path) -> None:
    path = tmp_path / "graduation.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
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
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
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
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    provider = PaddleOCRProvider(make_settings())
    provider.__dict__["_engine"] = _FakePaddleEngine(
        [
            [
                ([[0, 0], [100, 0], [100, 20], [0, 20]], ("사업자등록증", 0.99)),
                ([[0, 30], [140, 30], [140, 50], [0, 50]], ("상호 한국테크", 0.99)),
                ([[0, 60], [140, 60], [140, 80], [0, 80]], ("대표자 이영희", 0.99)),
                (
                    [[0, 90], [220, 90], [220, 110], [0, 110]],
                    ("사업자등록번호 123-45-67890", 0.99),
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
    assert issues


class _FakePaddleEngine:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def predict(self, path: str) -> object:
        return self.payload
