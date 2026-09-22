import pytest

from app.core.domain import EXPECTED_FIELDS, DocumentType
from app.document_intelligence.extraction.business_registration import BusinessRegistrationExtractor
from app.document_intelligence.extraction.career import CareerCertificateExtractor
from app.document_intelligence.extraction.enrollment import EnrollmentCertificateExtractor
from app.document_intelligence.extraction.graduation import GraduationCertificateExtractor
from app.document_intelligence.extraction.national_tax_payment import (
    NationalTaxPaymentCertificateExtractor,
)
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.extraction.sme_confirmation import SMEConfirmationExtractor
from app.document_intelligence.extraction.social_insurance_payment import (
    SocialInsurancePaymentCertificateExtractor,
)
from app.document_intelligence.extraction.transcript import TranscriptExtractor
from app.document_intelligence.normalization.field_normalizer import (
    normalize_business_number,
    normalize_date,
    normalize_gpa,
    normalize_gpa_scale,
    normalize_text_field,
)

GRADUATION_TEXT = (
    "졸업증명서\n성명 홍길동\n대학교 한국대학교\n학과 컴퓨터공학과\n학위 학사\n"
    "졸업일자 2024-02-20\n발급일자 2026-01-10"
)
CAREER_TEXT_EXPLICIT = (
    "경력증명서\n성명 김철수\n회사명 한국테크\n직위 대리\n담당업무 백엔드 개발\n"
    "입사일 2020-03-02\n퇴사일 2023-08-31\n발급일자 2026-01-15"
)
CAREER_TEXT_RANGE = "경력증명서\n성명 김철수\n회사명 한국테크\n재직기간 2020.03.02 ~ 2023.08.31"
BUSINESS_TEXT = (
    "사업자등록증\n상호 한국테크\n대표자 이영희\n사업자등록번호 123-45-67890\n"
    "사업장 소재지 서울특별시 강남구\n업태 서비스업\n종목 소프트웨어 개발\n발급일자 2026-01-05"
)
SME_TEXT = (
    "중소기업확인서\n기업명 한국테크\n대표자 이영희\n사업자등록번호 123-45-67890\n"
    "확인번호 SME-2026-001\n유효기간 2026-01-01 ~ 2027-12-31\n발급일자 2026-01-01"
)


def by_name(fields) -> dict:
    return {f.field_name: f for f in fields}


@pytest.mark.parametrize(
    "doc_type,extractor_cls",
    [
        (DocumentType.GRADUATION_CERTIFICATE, GraduationCertificateExtractor),
        (DocumentType.CAREER_CERTIFICATE, CareerCertificateExtractor),
        (DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, BusinessRegistrationExtractor),
        (DocumentType.SME_CONFIRMATION_CERTIFICATE, SMEConfirmationExtractor),
        (DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE, NationalTaxPaymentCertificateExtractor),
        (
            DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE,
            SocialInsurancePaymentCertificateExtractor,
        ),
        (DocumentType.ENROLLMENT_CERTIFICATE, EnrollmentCertificateExtractor),
        (DocumentType.TRANSCRIPT, TranscriptExtractor),
    ],
)
def test_extractor_field_names_match_expected_fields_contract(doc_type, extractor_cls) -> None:
    fields = extractor_cls().extract("")
    assert set(EXPECTED_FIELDS[doc_type]) <= {f.field_name for f in fields}


def test_graduation_extraction_happy_path() -> None:
    fields = by_name(GraduationCertificateExtractor().extract(GRADUATION_TEXT))
    assert fields["applicant_name"].normalized_value == "홍길동"
    assert fields["university_name"].normalized_value == "한국대학교"
    assert fields["graduation_date"].normalized_value == "2024-02-20"
    assert fields["issue_date"].normalized_value == "2026-01-10"
    # graduation_date and issue_date must be distinct, not the same value.
    assert fields["graduation_date"].normalized_value != fields["issue_date"].normalized_value


def test_graduation_extraction_tolerates_paddle_adjacent_values() -> None:
    text = "졸업증명서\n대학교 아자차대학교\n학위박사\n성명 박샘플\n졸업일자2020/04/04\n발급일자 2020년 5월 6일"
    fields = by_name(GraduationCertificateExtractor().extract(text))
    assert fields["applicant_name"].normalized_value == "박샘플"
    assert fields["degree"].normalized_value == "박사"
    assert fields["graduation_date"].normalized_value == "2020-04-04"
    assert fields["issue_date"].normalized_value == "2020-05-06"


def test_extraction_tolerates_next_line_values() -> None:
    text = "졸업증명서\n성명\n박샘플\n대학교\n아자차대학교\n학위\n박사"
    fields = by_name(GraduationCertificateExtractor().extract(text))
    assert fields["applicant_name"].normalized_value == "박샘플"
    assert fields["university_name"].normalized_value == "아자차대학교"
    assert fields["degree"].normalized_value == "박사"


def test_extraction_strips_trailing_merged_labels() -> None:
    text = "사업자등록증\n상호 한국테크 대표자 이영희 사업자등록번호 123 45 67890\n업태 서비스업 종목 소프트웨어 개발"
    fields = by_name(BusinessRegistrationExtractor().extract(text))
    assert fields["company_name"].normalized_value == "한국테크"
    assert fields["representative_name"].normalized_value == "이영희"
    assert fields["business_registration_number"].normalized_value == "1234567890"
    assert fields["business_type"].normalized_value == "서비스업"
    assert fields["business_item"].normalized_value == "소프트웨어 개발"


def test_graduation_extraction_missing_fields_are_null_not_guessed() -> None:
    fields = by_name(GraduationCertificateExtractor().extract("무관한 텍스트"))
    for field in fields.values():
        assert field.normalized_value is None
        assert field.needs_review is True


def test_label_without_separator_does_not_hallucinate_a_value() -> None:
    """Regression test (evaluation/reports/baseline_2026-09-09b.md, a real
    false-PASS finding): the label '학위' is a literal prefix of the real
    document title '학위수여증명서' with no separator between them. Before
    after_label() required an actual whitespace/colon separator, this
    matched with zero separator and returned '수여증명서' as the 'degree'
    value -- a hallucinated value from unrelated text, not a missing field."""
    text = "학위수여증명서\n성명 김테스트\n학위 석사"
    fields = by_name(GraduationCertificateExtractor().extract(text))
    assert fields["degree"].normalized_value == "석사"


def test_degree_label_does_not_match_certificate_title_without_value() -> None:
    fields = by_name(GraduationCertificateExtractor().extract("학위수여증명서\n성명 김테스트"))
    assert fields["degree"].normalized_value is None
    assert fields["degree"].needs_review is True


def test_career_extraction_explicit_dates() -> None:
    fields = by_name(CareerCertificateExtractor().extract(CAREER_TEXT_EXPLICIT))
    assert fields["employment_start_date"].normalized_value == "2020-03-02"
    assert fields["employment_end_date"].normalized_value == "2023-08-31"
    assert fields["company_name"].normalized_value == "한국테크"


def test_career_extraction_falls_back_to_range_label() -> None:
    fields = by_name(CareerCertificateExtractor().extract(CAREER_TEXT_RANGE))
    assert fields["employment_start_date"].normalized_value == "2020-03-02"
    assert fields["employment_end_date"].normalized_value == "2023-08-31"
    assert fields["employment_start_date"].needs_review is False


def test_career_extraction_multiple_periods_flagged_for_review() -> None:
    """Regression test for a P1.5 baseline finding (UNSUPPORTED_LAYOUT):
    when more than one employment period is present, the extractor must not
    silently present a confident single value -- it still returns its
    best-effort (first) period but flags it for review."""
    text = (
        "경력증명서\n성명 김철수\n회사명 한국테크\n"
        "재직기간 2018-04-17 ~ 2019-05-21\n재직기간 2019-07-20 ~ 2020-05-15"
    )
    fields = by_name(CareerCertificateExtractor().extract(text))
    assert fields["employment_start_date"].normalized_value == "2018-04-17"
    assert fields["employment_end_date"].normalized_value == "2019-05-21"
    assert fields["employment_start_date"].needs_review is True
    assert fields["employment_end_date"].needs_review is True


def test_business_registration_extraction_happy_path() -> None:
    fields = by_name(BusinessRegistrationExtractor().extract(BUSINESS_TEXT))
    assert fields["company_name"].normalized_value == "한국테크"
    assert fields["representative_name"].normalized_value == "이영희"
    assert fields["business_registration_number"].normalized_value == "1234567890"
    assert fields["business_registration_number"].raw_value == "123-45-67890"


def test_business_registration_official_form_labels() -> None:
    """Regression test: the officially annexed form ([별지 제6호서식],
    law.go.kr -- see evaluation/sources/source_registry.json
    src_business_01) uses '법인명칭' for company name and the compound
    '대표자 성명' for representative name, neither of which the original
    label lists (['상호','상호명'] / ['대표자','대표자명']) recognized."""
    text = (
        "사업자등록증\n법인명칭 예시산업 주식회사\n대표자 성명 박대표\n사업자등록번호 971-81-35937"
    )
    fields = by_name(BusinessRegistrationExtractor().extract(text))
    assert fields["company_name"].normalized_value == "예시산업 주식회사"
    assert fields["representative_name"].normalized_value == "박대표"


def test_mentor_business_label_and_opening_date_semantics() -> None:
    fields = by_name(
        BusinessRegistrationExtractor().extract(
            "사업자등록증\n법인명(단체명) 예시기업\n등록번호 123-45-67890\n개업연월일 2020-01-02"
        )
    )
    assert fields["company_name"].normalized_value == "예시기업"
    assert fields["issue_date"].normalized_value is None


def test_business_registration_number_false_positive_resistance() -> None:
    # An unrelated 10-digit run (e.g. a phone number) elsewhere in the text
    # must not be mistaken for the business registration number.
    text = "사업자등록증\n상호 한국테크\n연락처 010-1234-5678"
    fields = by_name(BusinessRegistrationExtractor().extract(text))
    assert fields["business_registration_number"].normalized_value is None
    assert fields["business_registration_number"].needs_review is True


def test_business_registration_number_unformatted_input() -> None:
    text = "사업자등록번호 1234567890"
    fields = by_name(BusinessRegistrationExtractor().extract(text))
    assert fields["business_registration_number"].normalized_value == "1234567890"


def test_business_registration_number_spaced_digits() -> None:
    text = "사업자등록번호 123 45 67890"
    fields = by_name(BusinessRegistrationExtractor().extract(text))
    assert fields["business_registration_number"].normalized_value == "1234567890"


def test_business_registration_number_tolerates_spaced_label() -> None:
    """Regression test for a P1.5 baseline finding: a label rendered with an
    internal space ("사업자 등록번호" instead of "사업자등록번호") was not
    recognized by exact label matching (evaluation/reports/
    baseline_2026-09-09.md, EXTRACTION_LABEL_ERROR)."""
    text = "사업자등록증\n상호 한국테크\n사업자 등록번호 123-45-67890"
    fields = by_name(BusinessRegistrationExtractor().extract(text))
    assert fields["business_registration_number"].normalized_value == "1234567890"


def test_graduation_date_label_tolerates_spaced_label() -> None:
    text = "졸업증명서\n성명 홍길동\n졸업 일자 2024-02-20"
    fields = by_name(GraduationCertificateExtractor().extract(text))
    assert fields["graduation_date"].normalized_value == "2024-02-20"


def test_label_spacing_tolerance_does_not_match_across_lines() -> None:
    """The spacing tolerance is deliberately restricted to spaces/tabs, not
    newlines -- a label split across two lines ("vertical" layout) is a
    separate, still-open limitation, not something this fix should mask."""
    text = "사업자등록증\n사업자\n등록번호 123-45-67890"
    fields = by_name(BusinessRegistrationExtractor().extract(text))
    # Documents the current behavior rather than asserting it is desirable:
    # "등록번호" alone (the fallback label) still matches on its own line.
    assert fields["business_registration_number"].normalized_value == "1234567890"


def test_sme_confirmation_extraction_happy_path() -> None:
    fields = by_name(SMEConfirmationExtractor().extract(SME_TEXT))
    assert fields["company_name"].normalized_value == "한국테크"
    assert fields["certificate_number"].normalized_value == "SME-2026-001"
    assert fields["valid_from"].normalized_value == "2026-01-01"
    assert fields["valid_until"].normalized_value == "2027-12-31"
    assert fields["issue_date"].normalized_value == "2026-01-01"


def test_sme_validity_period_normalizes_ocr_date_variants() -> None:
    text = "중소기업확인서\n기업명 한국테크\n유효기간 2026. 1. 1. ~ 2027년 12월 31일"
    fields = by_name(SMEConfirmationExtractor().extract(text))
    assert fields["valid_from"].normalized_value == "2026-01-01"
    assert fields["valid_until"].normalized_value == "2027-12-31"


def test_sme_confirmation_missing_validity_is_null() -> None:
    fields = by_name(SMEConfirmationExtractor().extract("중소기업확인서\n기업명 한국테크"))
    assert fields["valid_from"].normalized_value is None
    assert fields["valid_until"].normalized_value is None
    assert fields["valid_until"].needs_review is True


def test_sme_split_line_validity_range_is_supported() -> None:
    fields = by_name(
        SMEConfirmationExtractor().extract(
            "중소기업확인서\n유효기간\n2026년 1월 1일 ~ 2027년 12월 31일"
        )
    )
    assert fields["valid_from"].normalized_value == "2026-01-01"
    assert fields["valid_until"].normalized_value == "2027-12-31"


def test_new_mentor_extractors_preserve_structured_values() -> None:
    tax = by_name(
        NationalTaxPaymentCertificateExtractor().extract(
            "국세 납세증명서\n납세자명 한국테크\n사업자등록번호 123-45-67890\n"
            "발급일자 2026-01-01\n유효기간 2026-01-01 ~ 2026-02-01"
        )
    )
    assert tax["company_name"].normalized_value == "한국테크"
    assert tax["business_registration_number"].normalized_value == "1234567890"
    assert tax["valid_until"].normalized_value == "2026-02-01"

    social = by_name(
        SocialInsurancePaymentCertificateExtractor().extract(
            "4대 사회보험료 완납증명서\n사업장명 한국테크 본점\n사업자등록번호 1234567890\n"
            "발급일자 2026.01.02\n유효기한 2026.02.02"
        )
    )
    assert social["workplace_name"].normalized_value == "한국테크 본점"
    assert social["valid_until"].normalized_value == "2026-02-02"


def test_mentor_tax_and_student_aliases() -> None:
    tax = by_name(
        NationalTaxPaymentCertificateExtractor().extract(
            "납세증명서\n성명(상호) 예시기업\n사업자등록번호 123-45-67890\n"
            "증명서 유효기간 2026-12-31"
        )
    )
    assert tax["company_name"].normalized_value == "예시기업"
    assert tax["valid_until"].normalized_value == "2026-12-31"

    enrollment = by_name(
        EnrollmentCertificateExtractor().extract(
            "재학증명서\n성명 김학생\n대학 예시대학교\n발급일 2026-09-20"
        )
    )
    assert enrollment["university_name"].normalized_value == "예시대학교"
    assert enrollment["issue_date"].normalized_value == "2026-09-20"


def test_mentor_issue_number_and_total_gpa_aliases() -> None:
    sme = by_name(SMEConfirmationExtractor().extract("중소기업확인서\n발급번호 SME-001"))
    transcript = by_name(TranscriptExtractor().extract("성적증명서\n총평점 3.85 / 4.50"))
    assert sme["certificate_number"].normalized_value == "SME-001"
    assert transcript["gpa"].normalized_value == "3.85"
    assert transcript["gpa_scale"].normalized_value == "4.5"


def test_social_payment_number_is_not_a_business_registration_number() -> None:
    fields = by_name(
        SocialInsurancePaymentCertificateExtractor().extract(
            "4대 사회보험료 완납증명서\n통합납부자번호 123-45-67890\n사업장명 예시사업장"
        )
    )
    assert fields["business_registration_number"].normalized_value is None


def test_validity_is_not_guessed_from_unrelated_dates() -> None:
    tax = by_name(
        NationalTaxPaymentCertificateExtractor().extract(
            "납세증명서\n발급일 2026-09-20\n납부기한 2026-12-31"
        )
    )
    social = by_name(
        SocialInsurancePaymentCertificateExtractor().extract(
            "4대 사회보험료 완납증명서\n발급일 2026-09-20\n개업연월일 2020-01-01"
        )
    )
    assert tax["valid_until"].normalized_value is None
    assert social["valid_until"].normalized_value is None


def test_transcript_does_not_guess_issue_date_or_gpa_from_unlabeled_numbers() -> None:
    fields = by_name(
        TranscriptExtractor().extract(
            "성적증명서\n학번 20260001\n2026-09-20\n3학점\n4.0\n2026년도 1학기"
        )
    )
    assert fields["issue_date"].normalized_value is None
    assert fields["gpa"].normalized_value is None
    assert fields["gpa_scale"].normalized_value is None


def test_student_extractors_preserve_fields_and_numeric_gpa() -> None:
    enrollment = by_name(
        EnrollmentCertificateExtractor().extract(
            "재학증명서\n성명 김학생\n대학교 한국대학교\n학과 행정학과\n"
            "학번 20260001\n발급일자 2026-09-20"
        )
    )
    assert enrollment["student_name"].normalized_value == "김학생"
    assert enrollment["student_id"].normalized_value == "20260001"

    transcript = by_name(
        TranscriptExtractor().extract(
            "성적증명서\n성명 김학생\n대학교 한국대학교\n학번 20260001\n"
            "발급일자 2026-09-20\nGPA 3.85 / 4.50"
        )
    )
    assert transcript["gpa"].raw_value == "3.85 / 4.50"
    assert transcript["gpa"].normalized_value == "3.85"
    assert transcript["gpa_scale"].normalized_value == "4.5"


def test_registry_returns_empty_list_for_unknown() -> None:
    assert ExtractorRegistry().extract(DocumentType.UNKNOWN, "아무 텍스트") == []


def test_registry_dispatches_to_correct_extractor() -> None:
    fields = by_name(
        ExtractorRegistry().extract(DocumentType.GRADUATION_CERTIFICATE, GRADUATION_TEXT)
    )
    assert fields["applicant_name"].normalized_value == "홍길동"


@pytest.mark.parametrize("raw", ["123-45-67890", "123 45 67890", "1234567890"])
def test_normalize_business_number_to_comparison_digits(raw: str) -> None:
    assert normalize_business_number(raw) == "1234567890"


def test_normalize_business_number_rejects_wrong_length() -> None:
    assert normalize_business_number("12345") is None
    assert normalize_business_number("01234567890") is None


def test_normalize_gpa_and_scale() -> None:
    assert normalize_gpa("3.85 / 4.50") == "3.85"
    assert normalize_gpa_scale("3.85 / 4.50") == "4.5"
    assert normalize_gpa("4.8 / 4.5") is None
    assert normalize_gpa("not a grade") is None


def test_normalize_date_dot_format() -> None:
    assert normalize_date("2026. 9. 8.") == "2026-09-08"


def test_normalize_date_hyphen_format() -> None:
    assert normalize_date("2026-09-08") == "2026-09-08"


def test_normalize_date_slash_format() -> None:
    assert normalize_date("2026/09/08") == "2026-09-08"


def test_normalize_date_korean_format() -> None:
    assert normalize_date("2026년 01월 09일") == "2026-01-09"


def test_normalize_date_rejects_invalid_calendar_date() -> None:
    assert normalize_date("2026년 13월 40일") is None


def test_normalize_date_none_for_missing_value() -> None:
    assert normalize_date(None) is None
    assert normalize_date("no date here") is None


def test_normalize_text_field_collapses_whitespace_and_noise() -> None:
    assert normalize_text_field("  홍길동 \n") == "홍길동"
    assert normalize_text_field(": 한국테크 -") == "한국테크"


def test_normalize_text_field_preserves_korean_characters() -> None:
    assert normalize_text_field("한국대학교") == "한국대학교"
