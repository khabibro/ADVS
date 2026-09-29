"""Regression tests for the real-document audit findings.

Every test here corresponds to a failure that was reproduced on a real
Korean administrative document (or on a document built to have the same
structure). The synthetic mentor benchmark passed all of these cases before
the fixes, which is exactly why they were written.
"""

from __future__ import annotations

import fitz
import pytest

from app.core.config import Settings
from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import DocumentClassifier
from app.document_intelligence.extraction.fields import (
    is_institution,
    is_organisation,
    is_person_name,
    looks_like_boilerplate,
)
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.layout import build_rows
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage
from app.document_intelligence.ocr.providers import PaddleOCRProvider
from app.document_intelligence.preprocessing.processor import PdfProcessor, is_meaningful_text


def _row(y: float, texts: list[str], height: float = 60.0, x: float = 500.0) -> list[OCRLine]:
    """Build boxes sharing a visual baseline, spaced apart like a
    letter-spaced Korean form label."""
    lines: list[OCRLine] = []
    cursor = x
    for text in texts:
        width = 60 + 20 * len(text)
        lines.append(OCRLine(text, 0.97, BoundingBox(cursor, y, width, height)))
        cursor += width + 120
    return lines


def _document(pages: list[OCRPage]) -> OCRDocumentResult:
    return OCRDocumentResult(
        provider="paddle", pages=pages, assembled_text="\n\n".join(p.text for p in pages)
    )


# ---------------------------------------------------------------------------
# 1. LAYOUT_LOSS: a label the detector split across boxes
# ---------------------------------------------------------------------------


def test_letter_spaced_label_split_across_boxes_yields_the_value() -> None:
    """Real 재학증명서: "성" and "명:홍길동" arrive as two separate boxes on
    one visual row. Before the fix the label "성명" never appeared as a
    contiguous string, so student_name was silently unresolved."""
    lines = _row(900, ["성", "명:홍길동"])
    page = OCRPage(1, "".join(line.text for line in lines), lines, 0.97)
    fields = {
        field.field_name: field
        for field in ExtractorRegistry().extract(
            DocumentType.ENROLLMENT_CERTIFICATE, _document([page])
        )
    }
    assert fields["student_name"].normalized_value == "홍길동"
    # Evidence must point at the real boxes, not a fabricated merged line.
    assert fields["student_name"].evidence is not None
    assert [item.source_text for item in fields["student_name"].evidence] == ["성", "명:홍길동"]


def test_document_title_split_across_boxes_is_still_classifiable() -> None:
    """The root failure on the real document: the letter-spaced title was
    recognised as 재/학/증/5명/서, so the exact-substring signal
    "재학증명서" never matched and the type came out UNKNOWN."""
    split = _document([OCRPage(1, "", _row(400, ["재", "학", "증", "5명", "서"]), 0.97)])
    assert (
        DocumentClassifier().classify(split.assembled_text).predicted_type == DocumentType.UNKNOWN
    )

    repaired = _document([OCRPage(1, "", _row(400, ["재", "학", "증", "명", "서"]), 0.97)])
    result = DocumentClassifier().classify("재학증명서\n" + repaired.assembled_text)
    assert result.predicted_type == DocumentType.ENROLLMENT_CERTIFICATE


def test_primary_department_beats_secondary_double_major() -> None:
    """Real 재학증명서: 전 공:<primary> and 복 수 전 공:<second major> both
    contain the label 전공. First-match returned the double major; ranking
    must prefer the primary, which appears first on the form."""
    lines = _row(1200, ["전", "공:컴퓨터공학과"]) + _row(1300, ["복 수 전 공 :영어영문학과"])
    page = OCRPage(1, "".join(line.text for line in lines), lines, 0.97)
    fields = {
        field.field_name: field
        for field in ExtractorRegistry().extract(
            DocumentType.ENROLLMENT_CERTIFICATE, _document([page])
        )
    }
    assert fields["department"].normalized_value == "컴퓨터공학과"


# ---------------------------------------------------------------------------
# 2. PAGE_SCOPE: a label must never pair with a value on another page
# ---------------------------------------------------------------------------


def test_label_on_one_page_never_pairs_with_value_on_the_next() -> None:
    """Reproduced bug: a bare label at the end of page 1 paired with the
    first text of page 2, producing a value whose evidence spanned two
    unrelated pages."""
    pages = [
        OCRPage(1, "학번", [OCRLine("학번", 0.99, BoundingBox(100, 100, 80, 20))], 0.99),
        OCRPage(2, "202312345", [OCRLine("202312345", 0.99, BoundingBox(100, 100, 120, 20))], 0.99),
    ]
    fields = {
        field.field_name: field
        for field in ExtractorRegistry().extract(
            DocumentType.ENROLLMENT_CERTIFICATE, _document(pages)
        )
    }
    student_id = fields["student_id"]
    assert student_id.normalized_value is None
    assert student_id.needs_review is True
    # Nothing may be populated from a cross-page pairing.
    for field in fields.values():
        if field.evidence:
            page_numbers = {item.page_number for item in field.evidence}
            assert len(page_numbers) == 1, f"{field.field_name} spans pages {page_numbers}"


# ---------------------------------------------------------------------------
# 3. FIELD_CANDIDATE_RANKING / shape validation
# ---------------------------------------------------------------------------


def test_footnote_boilerplate_is_never_a_university_name() -> None:
    """Reproduced bug: the real document's verification footnote contains
    "우리 대학 및 www.certipia.com ...". The old first-match extractor
    returned that entire sentence as university_name with OCR confidence
    0.908 -- above the 0.90 evidence floor, so it was accepted as
    SUFFICIENT and could have driven a downstream comparison."""
    footnote = OCRLine(
        "[인터넷 발급] 우리 대학 및 www.certipia.com 원본 대조 메뉴에서 증명서 하단의 "
        "인터넷 발급번호 입력(발급일로부터 180일 이내) 또는 스마트폰 써트피아 앱으로",
        0.908,
        BoundingBox(221, 2825, 1809, 44),
    )
    page = OCRPage(1, footnote.text, [footnote], 0.908)
    fields = {
        field.field_name: field
        for field in ExtractorRegistry().extract(
            DocumentType.ENROLLMENT_CERTIFICATE, _document([page])
        )
    }
    assert fields["university_name"].normalized_value is None
    assert fields["university_name"].needs_review is True


def test_shape_validators_reject_impossible_values() -> None:
    assert is_person_name("홍길동") is True
    assert is_person_name("성명:홍길동") is False
    assert is_person_name("K00000000000") is False
    assert is_person_name("www.certipia.com") is False

    assert is_institution("경북대학교") is True
    assert is_institution("총") is False
    assert is_institution("및www.certipia.com 원본대조") is False

    assert is_organisation("(주)한빛") is True
    assert is_organisation("123-45-67890") is False

    assert looks_like_boilerplate("QR코드를 촬영하여") is True
    assert looks_like_boilerplate("한빛상사") is False


def test_empty_candidate_never_creates_a_false_populated_field() -> None:
    """A value that fails shape validation must degrade to unresolved, never
    to a confident wrong value."""
    label_only = OCRLine("성명", 0.99, BoundingBox(100, 100, 80, 20))
    page = OCRPage(1, "성명", [label_only], 0.99)
    fields = {
        field.field_name: field
        for field in ExtractorRegistry().extract(
            DocumentType.ENROLLMENT_CERTIFICATE, _document([page])
        )
    }
    assert fields["student_name"].normalized_value is None


# ---------------------------------------------------------------------------
# 4. FILENAME LEAKAGE
# ---------------------------------------------------------------------------


def test_filename_never_influences_classification() -> None:
    text = "성명 홍길동 학번 202312345"
    neutral = DocumentClassifier().classify(text, "real_0001_enrollment.pdf")
    misleading = DocumentClassifier().classify(text, "사업자등록증.pdf")
    assert neutral.predicted_type == misleading.predicted_type
    assert neutral.score == misleading.score
    # A filename alone must never produce a supported type.
    assert (
        DocumentClassifier().classify("", "성적증명서.pdf").predicted_type == DocumentType.UNKNOWN
    )


# ---------------------------------------------------------------------------
# 5. RASTERIZATION resolution
# ---------------------------------------------------------------------------


def test_render_scale_follows_configured_dpi() -> None:
    def scale_for(dpi: int) -> float:
        return PaddleOCRProvider._render_scale(dpi)

    assert scale_for(288) == pytest.approx(4.0)
    assert scale_for(144) == pytest.approx(2.0)
    # Clamped so an absurd setting cannot exhaust memory or silently degrade.
    assert scale_for(10) == pytest.approx(1.5)
    assert scale_for(100_000) == pytest.approx(6.0)
    assert Settings().paddle_ocr_render_dpi == 288


# ---------------------------------------------------------------------------
# 6. PDF_ROUTING: mixed digital + scanned pages
# ---------------------------------------------------------------------------


def test_meaningful_text_is_evaluated_per_page_not_per_document(tmp_path) -> None:
    """Reproduced bug: one digital page made the whole document skip OCR, so
    every scanned page in the same file silently contributed nothing."""
    text_page = fitz.open()
    page = text_page.new_page(width=595, height=842)
    page.insert_text((72, 100), "BUSINESS REGISTRATION CERTIFICATE")
    page.insert_text((72, 130), "Name Hanbit Co Registration No 123-45-67890 Address Seoul")
    text_page.new_page(width=595, height=842)  # a scanned page: no text layer
    text_page.save(tmp_path / "text_only.pdf")
    text_page.close()

    result = PdfProcessor().extract_text(tmp_path / "text_only.pdf")
    assert result.page_count == 2
    assert len(result.pages[0].text.strip()) == 91
    assert len(result.pages[1].text.strip()) == 0
    assert is_meaningful_text(result.pages[0].text) is True
    assert is_meaningful_text(result.pages[1].text) is False
    # The document-level aggregate stays meaningful, but a routing decision
    # must never be made from it alone.
    assert result.has_meaningful_text is True


# ---------------------------------------------------------------------------
# 7. Layout grouping invariants
# ---------------------------------------------------------------------------


def test_rows_group_only_boxes_that_share_a_baseline() -> None:
    lines = _row(900, ["성", "명:홍길동"]) + _row(1000, ["소", "속:컴퓨터공학과"])
    page = OCRPage(1, "", lines, 0.97)
    rows = build_rows(page)
    assert len(rows) == 2
    assert rows[0].text == "성 명:홍길동"
    assert rows[1].text == "소 속:컴퓨터공학과"
    # Segments keep their own geometry and confidence.
    assert [segment.confidence for segment in rows[0].segments] == [0.97, 0.97]
    assert all(segment.bounding_box is not None for segment in rows[0].segments)


def test_rows_without_geometry_keep_document_order() -> None:
    """A PDF text line PyMuPDF could not box must not be relocated to the end
    of the page, or "label on one line, value on the next" breaks."""
    lines = [
        OCRLine("성명", 0.98, None),
        OCRLine("김학생", 0.42, BoundingBox(1, 2, 3, 4)),
    ]
    rows = build_rows(OCRPage(1, "", lines, 0.9))
    assert [row.text for row in rows] == ["성명", "김학생"]
