"""Phase G / G-1: a PDF text layer is trusted only for text a person can see.

Fixtures are built in memory with PyMuPDF; every name, date and number is invented.
"""

import io
import uuid
from pathlib import Path

import fitz
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage
from app.document_intelligence.preprocessing.processor import PdfProcessor
from app.document_intelligence.preprocessing.text_layer import audit_text_layer, decision_tokens

VISIBLE = "졸업증명서 성명 홍길동 졸업일자 2024-02-20 발급일자 2026-01-10 한국대학교 컴퓨터공학과"
HIDDEN_DATE = "발급일자 2030-01-01"


def _pdf(tmp_path: Path, build) -> Path:
    doc = fitz.open()
    page = doc.new_page()
    build(page)
    path = tmp_path / f"{uuid.uuid4().hex}.pdf"
    doc.save(path)
    doc.close()
    return path


def _read(path: Path):
    return PdfProcessor().extract_text(path)


def _layer(result, index: int = 0) -> dict:
    return result.pages[index].metadata["text_layer"]


def _text(page: fitz.Page, y: float, text: str, **kwargs) -> None:
    page.insert_text((72, y), text, fontname="korea", fontsize=kwargs.pop("fontsize", 12), **kwargs)


# --- hidden text is not trusted -------------------------------------------------------------


def test_visible_digital_pdf_is_trusted_and_unchanged(tmp_path: Path) -> None:
    result = _read(_pdf(tmp_path, lambda page: _text(page, 72, VISIBLE)))
    assert result.has_meaningful_text
    assert "2024-02-20" in result.text
    assert _layer(result) == {"trusted": True, "reasons": [], "hidden_tokens": []}


def test_invisible_render_mode_text_is_not_returned_and_page_is_untrusted(tmp_path: Path) -> None:
    def build(page: fitz.Page) -> None:
        _text(page, 72, VISIBLE)
        _text(page, 100, HIDDEN_DATE, render_mode=3)

    result = _read(_pdf(tmp_path, build))
    assert "2030-01-01" not in result.text
    assert "2024-02-20" in result.text
    layer = _layer(result)
    assert layer["trusted"] is False
    assert "2030-01-01" in layer["hidden_tokens"]
    assert "render_mode_invisible" in layer["reasons"]


def test_white_on_white_text_is_not_returned(tmp_path: Path) -> None:
    def build(page: fitz.Page) -> None:
        _text(page, 72, VISIBLE)
        _text(page, 110, HIDDEN_DATE, color=(1, 1, 1))

    result = _read(_pdf(tmp_path, build))
    assert "2030-01-01" not in result.text
    assert _layer(result)["trusted"] is False
    assert "not_drawn" in _layer(result)["reasons"]


def test_tiny_and_off_page_text_is_not_returned(tmp_path: Path) -> None:
    def build(page: fitz.Page) -> None:
        _text(page, 72, VISIBLE)
        _text(page, 120, HIDDEN_DATE, fontsize=0.5)
        page.insert_text((2000, 140), HIDDEN_DATE, fontname="korea", fontsize=12)

    result = _read(_pdf(tmp_path, build))
    assert "2030-01-01" not in result.text
    assert _layer(result)["trusted"] is False


def test_text_covered_by_an_opaque_image_is_not_returned(tmp_path: Path) -> None:
    cover = io.BytesIO()
    Image.new("RGB", (400, 40), "white").save(cover, format="PNG")

    def build(page: fitz.Page) -> None:
        _text(page, 72, VISIBLE)
        _text(page, 130, HIDDEN_DATE)
        page.insert_image(
            fitz.Rect(60, 112, 460, 140), stream=cover.getvalue(), keep_proportion=False
        )

    result = _read(_pdf(tmp_path, build))
    assert "2030-01-01" not in result.text
    assert "not_drawn" in _layer(result)["reasons"]


def test_scan_probe_hidden_date_over_image_text_never_becomes_page_text(tmp_path: Path) -> None:
    """The Phase F probe: the page shows an image with an expired date, the invisible text layer
    claims a valid one."""
    picture = Image.new("RGB", (900, 160), "white")
    ImageDraw.Draw(picture).text((10, 10), "valid until 2025-01-31", fill="black")
    stream = io.BytesIO()
    picture.save(stream, format="PNG")

    def build(page: fitz.Page) -> None:
        page.insert_image(fitz.Rect(40, 60, 540, 150), stream=stream.getvalue())
        _text(
            page,
            100,
            "유효기간 2027-12-31 사업자등록번호 220-81-12341 주식회사 테스트상사",
            render_mode=3,
        )

    result = _read(_pdf(tmp_path, build))
    assert "2027-12-31" not in result.text
    assert not result.has_meaningful_text
    assert _layer(result)["trusted"] is False


def test_ocr_searchable_pdf_of_a_scan_is_not_a_digital_original(tmp_path: Path) -> None:
    """Scan + invisible OCR text layer (what "make searchable" tools produce)."""
    picture = Image.new("RGB", (600, 200), "white")
    stream = io.BytesIO()
    picture.save(stream, format="PNG")

    def build(page: fitz.Page) -> None:
        page.insert_image(page.rect, stream=stream.getvalue())
        _text(page, 100, VISIBLE, render_mode=3)

    result = _read(_pdf(tmp_path, build))
    assert not result.has_meaningful_text
    assert result.pages[0].metadata["source"] == "direct_pdf_text"
    assert _layer(result)["trusted"] is False


# --- pages that go to OCR for other reasons -------------------------------------------------


def test_unmapped_font_encoding_page_is_untrusted(tmp_path: Path) -> None:
    """Broken extractors leave `(cid:NN)` placeholders where the font has no Unicode map."""
    broken = " ".join(f"(cid:{number})" for number in range(100, 112))

    def build(page: fitz.Page) -> None:
        _text(page, 72, broken)

    layer = _layer(_read(_pdf(tmp_path, build)))
    assert layer["trusted"] is False
    assert "garbled_font_encoding" in layer["reasons"]


def test_private_use_and_replacement_characters_count_as_garbled() -> None:
    from app.document_intelligence.preprocessing.text_layer import _is_garbled

    assert _is_garbled("\ue001\ue002\ue003\ue004\ue005\ue006\ue007\ue008\ue009\ue00a\ue00b")
    assert _is_garbled("\ufffd" * 12)
    assert not _is_garbled(VISIBLE)


def test_hybrid_page_with_a_large_picture_is_untrusted(tmp_path: Path) -> None:
    picture = Image.new("RGB", (500, 500), (200, 200, 200))
    stream = io.BytesIO()
    picture.save(stream, format="PNG")

    def build(page: fitz.Page) -> None:
        page.insert_image(fitz.Rect(40, 200, 560, 760), stream=stream.getvalue())
        _text(page, 72, VISIBLE)

    layer = _layer(_read(_pdf(tmp_path, build)))
    assert layer["trusted"] is False
    assert "image_regions" in layer["reasons"]


def test_two_different_texts_on_top_of_each_other_are_untrusted(tmp_path: Path) -> None:
    def build(page: fitz.Page) -> None:
        _text(page, 72, "유효기간 2025-01-31 까지")
        _text(page, 72, "유효기간 2027-12-31 까지")

    layer = _layer(_read(_pdf(tmp_path, build)))
    assert layer["trusted"] is False
    assert "overlapping_text" in layer["reasons"]


def test_provenance_is_recorded_and_never_a_trust_signal(tmp_path: Path) -> None:
    path = _pdf(tmp_path, lambda page: _text(page, 72, VISIBLE))
    provenance = _read(path).provenance
    assert set(provenance) == {"producer", "creator", "has_signature_fields", "encrypted"}
    assert provenance["has_signature_fields"] is False


# --- consistency with the pixels ----------------------------------------------------------


def _ocr_page(text: str) -> OCRPage:
    return OCRPage(
        1,
        text,
        [OCRLine(text, 0.97, BoundingBox(0, 0, 100, 20))],
        0.97,
        metadata={"source": "ocr"},
    )


def test_audit_flags_hidden_tokens_the_pixels_do_not_show(tmp_path: Path) -> None:
    def build(page: fitz.Page) -> None:
        _text(page, 72, VISIBLE)
        _text(page, 100, HIDDEN_DATE, render_mode=3)

    embedded = _read(_pdf(tmp_path, build)).pages
    ocr = [_ocr_page("졸업증명서 졸업일자 2024-02-20 발급일자 2026-01-10")]
    audit = audit_text_layer(embedded, ocr, {})
    assert audit["mismatch"] is True
    assert audit["pages"][0]["hidden_tokens_not_on_page"] == ["2030-01-01"]
    assert audit["pages"][0]["text_used"] == "ocr"


def test_audit_accepts_hidden_text_that_matches_the_pixels(tmp_path: Path) -> None:
    """A scan with an OCR text layer: hidden text equal to what OCR reads is harmless."""

    def build(page: fitz.Page) -> None:
        _text(page, 72, VISIBLE, render_mode=3)

    embedded = _read(_pdf(tmp_path, build)).pages
    ocr = [_ocr_page("졸업증명서 졸업일자 2024-02-20 발급일자 2026-01-10")]
    assert audit_text_layer(embedded, ocr, {})["mismatch"] is False


def test_decision_tokens_normalise_dates_and_digit_runs() -> None:
    assert decision_tokens("유효기간 2027. 3. 5. 사업자 220-81-12341") == {
        "2027-03-05",
        "2208112341",
    }
    assert decision_tokens("page 12 of 30") == set()


# --- end to end: never READY ---------------------------------------------------------------


def test_hidden_date_pdf_is_ocr_read_flagged_and_never_ready(
    client: TestClient, db_session, monkeypatch
) -> None:
    from tests.test_pipeline_integration import (
        _create_project,
        _detail,
        _page,
        _process,
        _upload,
    )

    calls: list[int] = []

    class VisiblePageProvider:
        async def extract_document(self, *_args, **_kwargs):
            calls.append(1)
            return [
                _page(
                    1,
                    [
                        "졸업증명서",
                        "성명 홍길동",
                        "대학교 한국대학교",
                        "졸업일자 2024-02-20",
                        "발급일자 2026-01-10",
                    ],
                )
            ]

    monkeypatch.setattr(
        "app.services.processing.get_ocr_provider", lambda _settings: VisiblePageProvider()
    )
    doc = fitz.open()
    page = doc.new_page()
    _text(page, 72, VISIBLE)
    _text(page, 100, HIDDEN_DATE, render_mode=3)
    data = doc.tobytes()
    doc.close()

    project = _create_project(client, db_session, applicant_name="홍길동")
    document = _upload(client, project["id"], "hidden_date.pdf", data)
    processed = _process(client, document["id"])

    assert calls, "the untrusted page must be read from its pixels"
    assert processed["processing_status"] == "COMPLETED"
    assert processed["classification_meta"]["text_layer"]["mismatch"] is True
    detail = _detail(client, document["id"])
    assert detail["overall_status"] != "READY"
    assert any(item["code"] == "TEXT_LAYER_MISMATCH" for item in detail["validation_results"])
    fields = {item["field_name"]: item for item in detail["extracted_fields"]}
    assert fields["graduation_date"]["normalized_value"] == "2024-02-20"
    assert "2030-01-01" not in str(fields)
