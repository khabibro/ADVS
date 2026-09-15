from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import DocumentClassifier

GRADUATION_TEXT = "졸업증명서\n성명 홍길동\n대학교 한국대학교\n학과 컴퓨터공학과\n학위 학사\n졸업일자 2024-02-20"
CAREER_TEXT = "경력증명서\n성명 김철수\n회사명 한국테크\n직위 대리\n담당업무 백엔드 개발\n재직기간 2020-2023"
BUSINESS_TEXT = (
    "사업자등록증\n상호 한국테크\n대표자 이영희\n사업자등록번호 123-45-67890\n"
    "사업장 소재지 서울특별시\n업태 서비스업\n종목 소프트웨어"
)
SME_TEXT = "중소기업확인서\n기업명 한국테크\n사업자등록번호 123-45-67890\n유효기간 2026-01-01 ~ 2027-12-31"


def test_classifier_graduation_certificate() -> None:
    result = DocumentClassifier().classify(GRADUATION_TEXT)
    assert result.predicted_type == DocumentType.GRADUATION_CERTIFICATE
    assert result.confidence_score > 0.5
    assert result.needs_review is False


def test_classifier_career_certificate() -> None:
    result = DocumentClassifier().classify(CAREER_TEXT)
    assert result.predicted_type == DocumentType.CAREER_CERTIFICATE
    assert result.needs_review is False


def test_classifier_business_registration_certificate() -> None:
    result = DocumentClassifier().classify(BUSINESS_TEXT)
    assert result.predicted_type == DocumentType.BUSINESS_REGISTRATION_CERTIFICATE
    assert result.needs_review is False


def test_classifier_sme_confirmation_certificate() -> None:
    result = DocumentClassifier().classify(SME_TEXT)
    assert result.predicted_type == DocumentType.SME_CONFIRMATION_CERTIFICATE
    assert result.needs_review is False


def test_classifier_unknown_for_unrelated_text() -> None:
    result = DocumentClassifier().classify("무관한 문서입니다")
    assert result.predicted_type == DocumentType.UNKNOWN
    assert result.needs_review is True


def test_classifier_empty_text_is_unknown() -> None:
    result = DocumentClassifier().classify("")
    assert result.predicted_type == DocumentType.UNKNOWN
    assert result.needs_review is True
    assert result.confidence_score == 0.0


def test_generic_words_alone_do_not_force_classification() -> None:
    # "졸업" and "대학" are generic-weight signals; without the title or any
    # supporting label, evidence must stay below the confident-type floor.
    result = DocumentClassifier().classify("작년에 대학 졸업 이야기를 나눴다")
    assert result.predicted_type == DocumentType.UNKNOWN


def test_strong_title_evidence_alone_is_sufficient() -> None:
    result = DocumentClassifier().classify("사업자등록증")
    assert result.predicted_type == DocumentType.BUSINESS_REGISTRATION_CERTIFICATE
    assert result.confidence_score > 0.9


def test_ambiguous_document_requires_review() -> None:
    # Business registration and SME confirmation both carry a business
    # registration number; give them comparable supporting evidence with no
    # title for either so scores land close together.
    text = "사업자등록번호 123-45-67890\n상호 한국테크\n기업명 한국테크\n중소기업"
    result = DocumentClassifier().classify(text)
    assert result.needs_review is True


def test_conflicting_signals_do_not_produce_false_certainty() -> None:
    text = f"{GRADUATION_TEXT}\n{CAREER_TEXT}"
    result = DocumentClassifier().classify(text)
    # Both types now carry strong (title-level) evidence; whichever wins,
    # the near-tie must be flagged rather than asserted confidently.
    assert result.needs_review is True


def test_ocr_whitespace_and_linewrap_noise_is_tolerated() -> None:
    noisy = "사업자\n등록증\n상   호 한국테크\n대  표자 이영희"
    result = DocumentClassifier().classify(noisy)
    assert result.predicted_type == DocumentType.BUSINESS_REGISTRATION_CERTIFICATE


def test_support_only_evidence_without_title_or_identifier_is_unknown() -> None:
    """Regression test for a P1.5 baseline finding (evaluation/reports/
    baseline_2026-09-09.md): an enrollment certificate ("재학증명서") sharing
    only SUPPORT-weight vocabulary (대학교, 학과) with GRADUATION_CERTIFICATE,
    and no title or identifier-level signal, was confidently (0.99, no
    review) misclassified as GRADUATION_CERTIFICATE."""
    text = "재학증명서\n성명 김테스트\n대학교 가나다대학교\n학과 컴퓨터공학과\n재학 여부 재학중"
    result = DocumentClassifier().classify(text)
    assert result.predicted_type == DocumentType.UNKNOWN


def test_single_support_label_without_competition_is_unknown() -> None:
    """A single SUPPORT-weight label with no other evidence and no
    competing candidate must not be treated as confident proof."""
    result = DocumentClassifier().classify("근로계약서\n성명 이예시\n회사명 테스트테크 주식회사")
    assert result.predicted_type == DocumentType.UNKNOWN


def test_degree_conferment_certificate_title_recognized() -> None:
    """Regression test: '학위수여증명서' (degree conferment certificate) is a
    real, official alternate title for the same underlying credential as
    '졸업증명서' (confirmed via 정부24 and two university registrar pages --
    see evaluation/sources/source_registry.json). Before this was added as
    a TITLE-weight signal, a document using only this title classified as
    UNKNOWN (evaluation/reports/baseline_2026-09-09b.md)."""
    text = "학위수여증명서\n성명 김테스트\n대학교 아자차대학교\n학과 전자공학과\n학위 석사"
    result = DocumentClassifier().classify(text)
    assert result.predicted_type == DocumentType.GRADUATION_CERTIFICATE
    assert result.needs_review is False
