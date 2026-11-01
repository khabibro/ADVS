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
    result = assess_title([page(*chars, box("납세증명서", 280))], TAX, ["납세증명서"])
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


def test_a_field_label_far_to_the_left_on_the_title_row_is_not_part_of_the_title() -> None:
    # 근로복지공단 완납증명원: "발 급 번 호" and the checked insurance boxes share the title's row
    lines = [
        box("발 급 번 호", 82, width=120),
        box("☑ 산재보험료", 400, width=200),
        box("완납 증명원", 900, width=240),
    ]
    soc = DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
    assert assess_title([page(*lines)], soc, ["완납증명원"]).established


# ---- body labels establish a transcript whose title row carries unexplained characters (invented layout) ----

TRN_ROW = [box("가나", 80, width=100), box("성적증명서", 220)]  # unexplained characters before the title


def test_a_transcript_title_with_unexplained_characters_is_established_by_two_body_labels() -> None:
    evidence = ["성적증명서", "평점평균", "취득학점"]
    assert assess_title([page(*TRN_ROW)], TRN, evidence).established


def test_one_body_label_or_none_does_not_establish_it() -> None:
    assert not assess_title([page(*TRN_ROW)], TRN, ["성적증명서", "평점평균"]).established
    assert not assess_title([page(*TRN_ROW)], TRN, ["성적증명서"]).established


def test_a_supported_body_label_that_is_only_support_does_not_count() -> None:
    # 백분율 / 학번 / GPA are support signals, not identifier-level
    assert not assess_title([page(*TRN_ROW)], TRN, ["성적증명서", "백분율", "학번", "GPA"]).established


def test_the_enrolment_layout_and_the_tax_certificate_are_not_established_by_body_labels() -> None:
    enr_row = [box("가나", 80, width=100), box("재학증명서", 220)]
    assert not assess_title([page(*enr_row)], ENR, ["재학증명서", "재학기간", "재학여부"]).established
    tax_row = [box("가나", 80, width=100), box("납세증명서", 220)]
    assert not assess_title([page(*tax_row)], TAX, ["납세증명서", "체납", "유효기간"]).established


def test_a_look_alike_qualifier_before_a_transcript_title_is_still_a_near_match() -> None:
    # the look-alike check comes first: body labels never override it
    result = assess_title(
        [page(box("지빙세", 100, width=150), box("성적증명서", 280))], TRN, ["성적증명서", "평점평균", "취득학점"]
    )
    assert result.established is False and result.near_match == "지방세"
