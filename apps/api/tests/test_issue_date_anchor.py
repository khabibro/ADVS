"""Issue date in an unlabelled issuance block: seal fragments and shredded issuer text must not
make it disappear, and the anchor must not make a body date look like an issue date."""

from app.document_intelligence.extraction.enrollment import EnrollmentCertificateExtractor
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage


def _extract(rows: list[tuple[str, int, int, int]]) -> dict:
    lines = [OCRLine(text, 0.95, BoundingBox(x, y, w, 40)) for text, x, y, w in rows]
    page = OCRPage(page_number=1, text="", lines=lines, metadata={})
    values = EnrollmentCertificateExtractor().extract(OCRDocumentResult("x", [page], ""))
    return {v.field_name: v for v in values}


_HEAD = [
    ("재학증명서", 400, 100, 300),
    ("성 명 : 가나다", 250, 300, 400),
    ("재 학 학 년 : 4학년", 250, 360, 400),
]
_SENTENCE = ("위의 사실을 증명합니다.", 390, 1000, 380)
_DATE = ("2026년 10월 30일", 470, 1070, 330)  # right edge at x=800
_ISSUER = ("경 북 대 학 교 총 장", 250, 1125, 400)


def test_date_with_clear_seal_digit_fragment_is_found() -> None:
    values = _extract([*_HEAD, _SENTENCE, _DATE, ("1", 880, 1075, 20), _ISSUER])
    assert values["issue_date"].normalized_value == "2026-10-30"
    assert values["issue_date"].needs_review is True


def test_date_with_digit_touching_the_date_box_stays_unresolved() -> None:
    values = _extract([*_HEAD, _SENTENCE, _DATE, ("1", 805, 1075, 20), _ISSUER])
    assert values["issue_date"].normalized_value is None


def test_date_found_when_issuer_text_below_is_shredded() -> None:
    shredded = [("가", 720, 1105, 30), ("7", 880, 1110, 20), ("나", 820, 1125, 30)]
    values = _extract([*_HEAD, _SENTENCE, _DATE, *shredded])
    assert values["issue_date"].normalized_value == "2026-10-30"
    assert values["issue_date"].needs_review is True


def test_date_without_sentence_or_issuer_is_not_an_issue_date() -> None:
    values = _extract([*_HEAD, ("2026년 10월 30일", 470, 700, 330), ("학점 4.0", 250, 800, 200)])
    assert values["issue_date"].normalized_value is None


def test_two_different_bare_dates_stay_unresolved() -> None:
    other = ("2023년 9월 1일", 470, 700, 330)
    values = _extract([*_HEAD, other, _SENTENCE, _DATE, _ISSUER])
    assert values["issue_date"].normalized_value is None
