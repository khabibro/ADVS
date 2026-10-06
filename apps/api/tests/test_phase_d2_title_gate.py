"""Phase D2: an OCR-read document must prove its type before anything on it is auto-accepted;
a garbled look-alike qualifier makes it UNKNOWN. Made-up values only."""

from __future__ import annotations

import pytest

from app.core.domain import DocumentType
from app.document_intelligence.classification.title_gate import _near_lookalike, assess_title
from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage

TAX = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
ENR = DocumentType.ENROLLMENT_CERTIFICATE
TRN = DocumentType.TRANSCRIPT


def box(
    text: str, x: float, y: float = 100.0, width: float | None = None, height: float = 40.0
) -> OCRLine:
    return OCRLine(text, 0.97, BoundingBox(x, y, width or 40.0 * len(text), height))


def page(*lines: OCRLine) -> OCRPage:
    return OCRPage(
        1, "\n".join(item.text for item in lines), list(lines), metadata={"source": "ocr"}
    )


def test_clean_title_row_is_established() -> None:
    assert assess_title([page(box("납세증명서", 300))], TAX, ["납세증명서"]).established


@pytest.mark.parametrize(
    "qualifier", ["지방새", "지빙세", "X방세", "방세", "지세", "저방세", "지방셰"]
)
def test_garbled_localtax_qualifier_is_a_near_match(qualifier: str) -> None:
    result = assess_title(
        [page(box(qualifier, 100, width=200), box("납세증명서", 320))], TAX, ["납세증명서"]
    )
    assert result.established is False
    assert result.near_match == "지방세"


def test_garbled_qualifier_spread_over_single_character_boxes_is_found_in_the_row() -> None:
    chars = [box(char, 100 + index * 45, width=40) for index, char in enumerate("지빙세")]
    result = assess_title([page(*chars, box("납세증명서", 320))], TAX, ["납세증명서"])
    assert result.near_match == "지방세"


@pytest.mark.parametrize(
    ("document_type", "title", "qualifier"),
    [(ENR, "재학증명서", "휴힉"), (ENR, "재학증명서", "후학")],
)
def test_garbled_leave_of_absence_qualifier_is_a_near_match(
    document_type, title, qualifier
) -> None:
    result = assess_title(
        [page(box(qualifier, 100, width=120), box(title, 240))], document_type, [title]
    )
    assert result.near_match == "휴학"


def test_genuine_qualifiers_and_titles_are_established() -> None:
    assert assess_title(
        [page(box("국세", 100, width=80), box("납세증명서", 200))], TAX, ["납세증명서"]
    ).established
    assert assess_title(
        [page(box("재 학 증 명 서", 200, width=300))], ENR, ["재학증명서"]
    ).established
    assert assess_title(
        [page(box("[로고 생략]", 40, width=200), box("납세증명서", 300))], TAX, ["납세증명서"]
    ).established


def test_exact_unrelated_words_are_unexplained_but_not_a_lookalike() -> None:
    result = assess_title(
        [page(box("대한민국", 100, width=160), box("납세증명서", 280))], TAX, ["납세증명서"]
    )
    assert result.established is False
    assert result.near_match is None
    assert result.reason == "UNEXPLAINED_CHARACTERS_BEFORE_TITLE"


def test_title_not_read_but_two_identifier_signals_agree_is_established() -> None:
    lines = [
        box("1적증명서", 200, width=240),
        box("취득학점 17", 100, 300),
        box("평점평균 3.4/4.5", 100, 360),
    ]
    assert assess_title([page(*lines)], TRN, ["평점평균", "취득학점", "학번"]).established
    assert not assess_title([page(*lines)], TRN, ["학번"]).established


def test_a_similar_looking_name_is_not_a_qualifier_match() -> None:
    # exactly one position must be a table confusion; two differences are not a near-match
    assert _near_lookalike("정빙새") is None
    assert _near_lookalike("가나다") is None
    assert (
        _near_lookalike("지방세") is None
    )  # exact qualifier is handled by the look-alike title table
