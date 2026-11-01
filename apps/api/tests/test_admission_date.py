"""The admission date is read beside its label, under it, or before the word 입학 (invented values)."""

from app.document_intelligence.extraction.enrollment import EnrollmentCertificateExtractor
from app.document_intelligence.extraction.transcript import TranscriptExtractor


def admission(text: str, extractor=None) -> str | None:
    values = {v.field_name: v for v in (extractor or TranscriptExtractor()).extract(text)}
    return values["admission_date"].normalized_value


def test_labelled_forms() -> None:
    assert admission("입학일자 : 2021년 3월 2일\n성명 : 가나다") == "2021-03-02"
    assert admission("입학일\n2021/03/02\n성명 : 가나다") == "2021-03-02"


def test_date_before_the_word_in_one_box() -> None:
    text = "재 학 증 명 서\n2021년 03월 02일 입학\n재학중"
    assert admission(text, EnrollmentCertificateExtractor()) == "2021-03-02"


def test_two_candidate_dates_or_no_word_stay_missing() -> None:
    assert admission("2021년 03월 02일 입학\n2020년 03월 02일 입학") is None
    assert admission("2021년 03월 02일 발급\n위의 사실을 증명합니다") is None
    assert admission("2021년 03월 02일 입학일") is None  # a label, not the word that follows a date
