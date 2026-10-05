"""Phase C C-1: genuine title variants classify; look-alikes stay UNKNOWN.
Hold-out values only."""

from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import DocumentClassifier


def test_classifier_accepts_wanapjeungmyeongwon_title_form() -> None:
    # 고용·산재보험료 완납증명원 is the 근로복지공단 title form (원, not 서).
    text = "☑ 고용보험료\n☑ 산재보험료\n완납 증명원\n사업장명 주식회사 가온정밀\n사업자등록번호 123-45-67890"
    assert DocumentClassifier().classify(text).predicted_type == (
        DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
    )


def test_classifier_keeps_wanapjeungmyeongseo_title_form() -> None:
    text = "4대 사회보험료 완납증명서\n사업장명 가온정밀"
    assert DocumentClassifier().classify(text).predicted_type == (
        DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
    )


def test_wanapjeungmyeongwon_does_not_override_lookalike_titles() -> None:
    text = "지방세납세증명서\n완납 증명원\n사업장명 가온정밀"
    assert DocumentClassifier().classify(text).predicted_type == DocumentType.UNKNOWN


def test_bare_wanap_phrase_without_title_is_not_social_insurance() -> None:
    text = "안내문\n보험료 납부 안내\n사업자등록번호 123-45-67890"
    assert DocumentClassifier().classify(text).predicted_type != (
        DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
    )
