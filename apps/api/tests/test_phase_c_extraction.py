"""Phase C: classification and extraction gaps on clean digital PDFs.

Every input here uses *hold-out* values (names, numbers, issuers) that are not
in the evaluation corpus, so a fix that merely memorised the corpus fails.
Each test names the real-world form variant it covers.
"""

from __future__ import annotations

from app.core.domain import DocumentType
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage

H = 14.0


def seg(text: str, x: float, y: float, w: float | None = None) -> OCRLine:
    width = w if w is not None else max(8.0, 7.0 * len(text))
    return OCRLine(
        text=text, confidence=None, bounding_box=BoundingBox(x=x, y=y, width=width, height=H)
    )


def doc(lines: list[OCRLine]) -> OCRDocumentResult:
    page = OCRPage(
        page_number=1,
        text="\n".join(line.text for line in lines),
        lines=lines,
        metadata={"source": "direct_pdf_text"},
    )
    return OCRDocumentResult("direct_pdf_text", [page], page.text)


def fields(doc_type: DocumentType, lines: list[OCRLine]) -> dict[str, str | None]:
    return {
        value.field_name: value.normalized_value
        for value in ExtractorRegistry().extract(doc_type, doc(lines))
    }


# ------------------------------------------------------------ C-2 extraction


def test_value_cell_with_leading_colon_is_read() -> None:
    # Letter-spaced label cell, then a separate value cell that starts with ": ".
    lines = [
        seg("사업자등록증", 200, 40),
        seg("법 인 명 ( 단 체 명 )", 60, 100, 85),
        seg(": 주식회사 가온정밀", 164, 100, 104),
        seg("대        표        자", 60, 130, 69),
        seg(": 이한솔", 164, 130, 41),
    ]
    got = fields(DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, lines)
    assert got["company_name"] == "주식회사 가온정밀"
    assert got["representative_name"] == "이한솔"


def test_parenthesised_label_cell_is_read() -> None:
    # 납세증명서 prints the number under "주민등록번호 (사업자등록번호)".
    lines = [
        seg("납세증명서", 200, 40),
        seg("주민등록번호", 60, 100),
        seg("(사업자등록번호)", 150, 100, 110),
        seg("123-45-67890", 280, 100),
    ]
    got = fields(DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE, lines)
    assert got["business_registration_number"] == "1234567890"


def test_parenthesised_label_stacked_under_another_label() -> None:
    # 납세증명서: "주민등록번호" over "(사업자등록번호)", value centred to the right
    # so it overlaps the lower (label) line by slightly under half its height.
    lines = [
        seg("납세증명서", 200, 40),
        seg("주민등록번호", 370, 100, 54),
        seg("(사업자등록번호)", 370, 114, 69),
        seg("123-45-67891", 463, 106, 55),
    ]
    got = fields(DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE, lines)
    assert got["business_registration_number"] == "1234567891"


def test_two_line_label_with_parenthetical_second_line() -> None:
    # 사업자등록번호 / (법인등록번호) stacked in one label cell, value to the right
    # of the second line (근로복지공단 완납증명원).
    lines = [
        seg("완납 증명원", 200, 40),
        seg("사 업 장 명", 60, 80),
        seg("주식회사 가온정밀", 160, 80),
        seg("사업자등록번호", 60, 120, 63),
        seg("(법인등록번호)", 61, 134, 60),
        seg("123-45-67890", 160, 127, 61),
    ]
    got = fields(DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE, lines)
    assert got["business_registration_number"] == "1234567890"
    assert got["workplace_name"] == "주식회사 가온정밀"


def test_checkbox_label_does_not_produce_a_business_number() -> None:
    lines = [
        seg("완납 증명원", 200, 40),
        seg("☐ 사업자등록번호", 60, 120),
    ]
    got = fields(DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE, lines)
    assert got["business_registration_number"] is None


def test_enrollment_affiliation_label_and_issuer_university() -> None:
    # 소속 prints "단과대학 학과"; the university appears in the issuer line.
    lines = [
        seg("재 학 증 명 서", 200, 40),
        seg("성           명", 60, 100, 70),
        seg(": 최도윤", 164, 100, 41),
        seg("소           속", 60, 130, 70),
        seg(": 인문대학 국어국문학과", 164, 130, 110),
        seg("학           번", 60, 160, 70),
        seg(": 2021987654", 164, 160, 70),
        seg("한 국 샘 플 대 학 교 총 장", 160, 400, 150),
    ]
    got = fields(DocumentType.ENROLLMENT_CERTIFICATE, lines)
    assert got["student_name"] == "최도윤"
    assert got["department"] == "국어국문학과"
    assert got["student_id"] == "2021987654"
    assert got["university_name"] == "한국샘플대학교"


def test_department_prefers_affiliation_over_secondary_major() -> None:
    lines = [
        seg("재학증명서", 200, 40),
        seg("소           속", 60, 100, 70),
        seg(": 공과대학 기계공학과", 164, 100, 110),
        seg("전           공", 60, 130, 70),
        seg(": 로봇융합전공", 164, 130, 70),
    ]
    assert fields(DocumentType.ENROLLMENT_CERTIFICATE, lines)["department"] == "기계공학과"


def test_two_different_issuer_universities_abstain() -> None:
    lines = [
        seg("재학증명서", 200, 40),
        seg("한국샘플대학교 총장", 160, 400),
        seg("미래예시대학교 총장", 160, 430),
    ]
    assert fields(DocumentType.ENROLLMENT_CERTIFICATE, lines)["university_name"] is None


def test_transcript_cumulative_gpa_follows_total_credits_row() -> None:
    lines = [
        seg("성적증명서", 200, 40),
        seg("평점평균: 3.10/4.5 백분율: 85.00/100", 60, 100, 200),
        seg("평점평균: 4.00/4.5 백분율: 93.00/100", 60, 130, 200),
        seg("총 취득학점: 70", 60, 170, 90),
        seg("평점평균: 3.55/4.5 백분율: 88.00/100", 60, 184, 200),
    ]
    got = fields(DocumentType.TRANSCRIPT, lines)
    assert got["gpa"] == "3.55"
    assert got["gpa_scale"] == "4.5"


def test_transcript_cumulative_gpa_from_header_table_cell() -> None:
    # Header cell "총평점평균" with the value in the cell directly below it.
    lines = [
        seg("성적증명서", 200, 40),
        seg("총취득학점", 300, 100, 60),
        seg("총평점평균", 380, 100, 60),
        seg("백분율환산", 460, 100, 60),
        seg("98", 310, 120, 20),
        seg("3.42 / 4.3", 380, 120, 60),
        seg("88.10 / 100", 460, 120, 60),
        seg("평점평균: 2.00/4.3 백분율: 70.00/100", 60, 300, 200),
    ]
    got = fields(DocumentType.TRANSCRIPT, lines)
    assert got["gpa"] == "3.42"
    assert got["gpa_scale"] == "4.3"


def test_conflicting_semester_gpas_without_cumulative_cue_still_abstain() -> None:
    lines = [
        seg("성적증명서", 200, 40),
        seg("평점평균: 3.10/4.5 백분율: 85.00/100", 60, 100, 200),
        seg("평점평균: 4.00/4.5 백분율: 93.00/100", 60, 130, 200),
    ]
    got = fields(DocumentType.TRANSCRIPT, lines)
    assert got["gpa"] is None
