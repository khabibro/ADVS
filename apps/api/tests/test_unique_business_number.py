"""Business number: label split or parenthesised -> the one valid hyphenated number is used (invented numbers)."""

from app.document_intelligence.extraction.national_tax_payment import (
    NationalTaxPaymentCertificateExtractor,
)
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage

VALID = "123-45-67891"
OTHER_VALID = "214-86-55302"
CHECKSUM_FAIL = "123-45-67890"


def _brn(rows: list[tuple[str, int]]) -> dict:
    lines = [OCRLine(text, 0.95, BoundingBox(100, y, 500, 40)) for text, y in rows]
    page = OCRPage(page_number=1, text="", lines=lines, metadata={})
    values = NationalTaxPaymentCertificateExtractor().extract(OCRDocumentResult("x", [page], ""))
    return {v.field_name: v for v in values}


def test_number_beside_a_parenthesised_label_is_found() -> None:
    values = _brn([("납세증명서", 50), ("(사업자등록번호)", 200), (VALID, 400)])
    value = values["business_registration_number"]
    assert value.normalized_value == VALID.replace("-", "")
    assert value.extraction_method == "regex_business_number_unique"


def test_two_different_valid_numbers_stay_unresolved() -> None:
    values = _brn([("납세증명서", 50), ("(사업자등록번호)", 200), (VALID, 400), (OTHER_VALID, 460)])
    assert values["business_registration_number"].normalized_value is None


def test_the_same_number_printed_twice_is_one_number() -> None:
    values = _brn([("납세증명서", 50), ("(사업자등록번호)", 200), (VALID, 400), (VALID, 460)])
    assert values["business_registration_number"].normalized_value == VALID.replace("-", "")


def test_a_number_failing_the_check_digit_is_not_taken_by_the_fallback() -> None:
    values = _brn([("납세증명서", 50), ("(사업자등록번호)", 200), (CHECKSUM_FAIL, 400)])
    assert values["business_registration_number"].normalized_value is None
