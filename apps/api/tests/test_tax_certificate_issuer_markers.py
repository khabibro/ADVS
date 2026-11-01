"""National vs local tax certificates: the issuer words decide, not only the (possibly split) title."""

from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import DocumentClassifier

NATIONAL = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE


def classify(text: str):
    return DocumentClassifier().classify(text)


def test_national_certificate_with_national_issuer_is_accepted_without_review() -> None:
    result = classify("납세증명서 납세자명 가나다상사 사업자등록번호 000-00-00000 유효기한 2099-01-31 ○○세무서장")
    assert result.predicted_type == NATIONAL
    assert result.needs_review is False


def test_local_certificate_with_a_split_title_is_not_typed_national() -> None:
    # The title is split by the layout, so the contiguous look-alike title never occurs.
    text = "납세 증명서 (납세자용) 지방 세 완납 내역 납세자명 가나다상사 징수 ○○구청장 지방세 징수법"
    result = classify(text)
    assert result.predicted_type == DocumentType.UNKNOWN
    assert result.needs_review is True


def test_local_marker_wins_even_when_a_national_word_is_also_present() -> None:
    result = classify("납세증명서 납세자명 가나다상사 유효기한 2099-01-31 지방세 위택스 국세와 구분")
    assert result.predicted_type == DocumentType.UNKNOWN


def test_national_certificate_without_any_issuer_word_goes_to_review() -> None:
    result = classify("납세증명서 납세자명 가나다상사 사업자등록번호 000-00-00000 유효기한 2099-01-31")
    assert result.predicted_type == NATIONAL
    assert result.needs_review is True
