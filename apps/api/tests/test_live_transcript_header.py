"""Item 10: the header of a transcript read from a photo or scan. Label spacing, colon variants, several label:value
pairs on one row, an eight-digit date, and an issuer line that is letter-spaced with a stray mark or a stamp over its
last characters. General rules only; invented values."""

from __future__ import annotations

import pytest

from app.document_intelligence.extraction.enrollment import EnrollmentCertificateExtractor
from app.document_intelligence.extraction.transcript import TranscriptExtractor
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage


def _page(rows: list[str]) -> OCRDocumentResult:
    lines = [
        OCRLine(
            text=text, confidence=0.97, bounding_box=BoundingBox(100, 100 + 120 * index, 900, 60)
        )
        for index, text in enumerate(rows)
    ]
    text = "\n".join(rows)
    return OCRDocumentResult("t", [OCRPage(1, text, lines)], text)


def _values(rows: list[str], extractor=None) -> dict[str, str | None]:
    result = (extractor or TranscriptExtractor()).extract(_page(rows))
    return {item.field_name: item.normalized_value for item in result}


BODY = ["성명 : 가나다", "생년월일 : 1999.3.7", "입학일자 : 2023.9.1", "학번 : 2023111111"]


@pytest.mark.parametrize(
    "issuer",
    [
        "가나대학교 총장",
        "가 나 대 학 교 총 장",
        '가 나 대학"교 총',  # a mark inside the line, the title cut by the stamp
        "가 나 대 학 교 총",
        "가나대학교총",
    ],
)
@pytest.mark.parametrize("extractor", [TranscriptExtractor, EnrollmentCertificateExtractor])
def test_university_from_the_issuer_line(issuer: str, extractor) -> None:
    got = _values([*BODY, "2026년 10월 30일", issuer], extractor())
    assert got["university_name"] == "가나대학교"


def test_letter_spaced_labels_and_colon_variants() -> None:
    rows = [
        "성 명 ： 가나다",
        "생 년 월 일 : 19990307",
        "입 학 일 자 ： 2023년 9월 1일",
        "학 번 : 2023111111",
    ]
    got = _values(rows)
    assert got["student_name"] == "가 나 다" or got["student_name"] == "가나다"
    assert got["birth_date"] == "1999-03-07"
    assert got["admission_date"] == "2023-09-01"
    assert got["student_id"] == "2023111111"


def test_several_label_value_pairs_on_one_row() -> None:
    got = _values(["성명: 가나다   생년월일: 1999-03-07   입학일자: 2023-09-01"])
    assert got["student_name"] == "가나다"
    assert got["birth_date"] == "1999-03-07"
    assert got["admission_date"] == "2023-09-01"


def test_an_eight_digit_number_is_a_date_only_after_a_date_label() -> None:
    assert _values(["학번: 20231111"])["birth_date"] is None
    assert _values(["학번: 20231111"])["student_id"] == "20231111"
    assert _values(["생년월일: 19990307"])["birth_date"] == "1999-03-07"
    assert _values(["생년월일: 19991378"])["birth_date"] is None  # not a calendar date


def test_two_different_universities_stay_unanswered() -> None:
    got = _values(["가나대학교 총장", "다라대학교 총장"])
    assert got["university_name"] is None
