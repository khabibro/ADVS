"""An enrolment certificate with a damaged title is recognised by its body labels, never when any word of another
student status (휴학, 졸업, 수료, 제적) is on the document (invented layouts, invented values)."""

from __future__ import annotations

import pytest

from app.core.domain import DocumentType
from app.document_intelligence.classification.body_labels import enrolment_body_labels
from app.document_intelligence.classification.classifier import DocumentClassifier
from app.document_intelligence.classification.title_gate import assess_title
from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage

ENR = DocumentType.ENROLLMENT_CERTIFICATE


def layout(title: str, *, status_label: str = "재학기간", attestation: str = "위의 사실을 증명합니다.") -> str:
    return "\n".join(
        [
            title,
            "성 명 : 류하늘",
            "소 속 : 자연과학대학 통계학과",
            "학 번 : 2030123456",
            f"{status_label} : 2030년 03월 02일 입학",
            "학 년 (학기) : 3 학년 (2학기)",
            "입학일자 : 2030년 03월 02일",
            attestation,
            "2030년 10월 07일",
            "가상과학기술대학교 총장",
        ]
    )


def classify(text: str) -> DocumentType:
    return DocumentClassifier().classify(text).predicted_type


def test_a_damaged_title_with_the_enrolment_body_is_recognised() -> None:
    text = layout("재 확 증 멍 서").replace("재학기간", "재학 상태")
    assert enrolment_body_labels("".join(text.split()))
    assert classify(text) == ENR


@pytest.mark.parametrize(
    ("title", "label"),
    [
        ("휴 힉 증 멍 서", "휴학기간"),  # a 휴학증명서 whose title is damaged: its own word is in the body
        ("졸 얼 예 정 증 멍 서", "졸업예정일"),
        ("수 로 증 멍 서", "수료일"),
        ("제 적 증 멍 서", "제적일"),
    ],
)
def test_a_word_of_another_status_anywhere_rules_the_enrolment_certificate_out(title: str, label: str) -> None:
    text = layout(title, status_label=label)
    assert not enrolment_body_labels("".join(text.split()))
    assert classify(text) != ENR


def test_the_word_counts_even_when_it_is_far_from_the_labels() -> None:
    text = layout("재 확 증 멍 서") + "\n비고 : 이 학생은 2029년에 휴학한 사실이 있음"
    assert classify(text) != ENR


def test_a_transcript_is_not_an_enrolment_certificate_by_its_shared_labels() -> None:
    text = layout("성 적 증 멍 서") + "\n취득학점: 17\n평점평균: 3.50/4.5 백분율: 88.00/100"
    assert not enrolment_body_labels("".join(text.split()))
    assert classify(text) != ENR


def test_the_semester_heading_of_a_transcript_is_not_the_year_of_study() -> None:
    text = "\n".join(["성 명 : 류하늘", "소 속 : 통계학과", "입학일자 : 2030년 03월 02일", "<<2030학년도 1학기>>", "재학 중", "증명합니다"])
    assert not enrolment_body_labels("".join(text.split()))


def test_without_the_attestation_the_body_alone_is_not_enough() -> None:
    assert not enrolment_body_labels("".join(layout("재 확 증 멍 서", attestation="").split()))


def line(text: str, y: float) -> OCRLine:
    return OCRLine(text, 0.95, BoundingBox(100, y, 40.0 * len(text), 40))


def page_of(text: str) -> OCRPage:
    lines = [line(part, 60 + 60 * i) for i, part in enumerate(text.splitlines())]
    return OCRPage(1, text, lines, metadata={"source": "ocr"})


def test_the_title_gate_establishes_such_a_document_and_only_such_a_document() -> None:
    from app.document_intelligence.classification.body_labels import BODY_LABELS_EVIDENCE

    good = page_of(layout("재 확 증 멍 서"))
    assert assess_title([good], ENR, list(BODY_LABELS_EVIDENCE)).established
    # the same evidence tokens do not establish a document that carries a word of another status
    other = page_of(layout("재 확 증 멍 서", status_label="휴학기간"))
    assert not assess_title([other], ENR, list(BODY_LABELS_EVIDENCE)).established
    # and ordinary evidence (a title or labels of the classifier) never takes this path
    assert not assess_title([good], ENR, ["재학기간"]).established
