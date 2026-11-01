"""The cumulative GPA is located by its total-credits line. A recogniser may misread one syllable of that
label (or of 평점평균); the line is still found, a semester line is never mistaken for the total, and the
value still comes from the 평점평균 "x/y" line with its own scale. All inputs are invented."""

from __future__ import annotations

import pytest

from app.core.domain import DocumentType
from app.document_intelligence.label_tolerance import find_label, starts_with_label
from tests.test_phase_c_extraction import fields, seg


def semester_page(total_label: str, gpa_label: str = "평점평균", scale: str = "4.5") -> list:
    return [
        seg("성적증명서", 200, 40),
        seg("취득학점: 15", 60, 100, 90),
        seg(f"{gpa_label}: 3.10/{scale} 백분율: 85.00/100", 60, 120, 220),
        seg("취득학점: 17", 60, 160, 90),
        seg(f"{gpa_label}: 4.00/{scale} 백분율: 93.00/100", 60, 180, 220),
        seg("취득학점: 18", 60, 220, 90),
        seg(f"{gpa_label}: 3.30/{scale} 백분율: 87.00/100", 60, 240, 220),
        seg(f"{total_label}: 50", 60, 280, 90),
        seg(f"{gpa_label}: 3.55/{scale} 백분율: 88.00/100", 60, 300, 220),
    ]


@pytest.mark.parametrize(
    "total_label", ["총 취득학점", "총 취득학정", "총 취두학점", "종 취득학점"]
)
def test_total_credits_label_with_one_misread_syllable_still_anchors(total_label: str) -> None:
    got = fields(DocumentType.TRANSCRIPT, semester_page(total_label))
    assert got["gpa"] == "3.55"
    assert got["gpa_scale"] == "4.5"


def test_scale_comes_from_the_line_itself() -> None:
    got = fields(DocumentType.TRANSCRIPT, semester_page("총 취득학정", scale="4.3"))
    assert (got["gpa"], got["gpa_scale"]) == ("3.55", "4.3")


def test_gpa_label_with_one_misread_syllable_is_read() -> None:
    got = fields(DocumentType.TRANSCRIPT, semester_page("총 취득학정", gpa_label="평정평균"))
    assert got["gpa"] == "3.55"


def test_sum_cue_anchors_when_the_prefix_of_the_total_label_is_garbled() -> None:
    lines = semester_page("총 취득학점")
    lines[7] = seg(
        "흉종 취득학점: 50", 60, 280, 90
    )  # the label cue fails; 15 + 17 + 18 = 50 proves the total
    assert fields(DocumentType.TRANSCRIPT, lines)["gpa"] == "3.55"


def test_a_wrong_sum_never_anchors() -> None:
    lines = semester_page("총 취득학점")
    lines[7] = seg("흉종 취득학점: 51", 60, 280, 90)  # 15 + 17 + 18 != 51: no proof, no anchor
    assert fields(DocumentType.TRANSCRIPT, lines)["gpa"] is None


def test_a_semester_line_is_never_taken_for_the_total() -> None:
    lines = [
        seg("성적증명서", 200, 40),
        seg("취득학점: 15", 60, 100, 90),
        seg("평점평균: 3.10/4.5 백분율: 85.00/100", 60, 120, 220),
        seg("취득학점: 17", 60, 160, 90),
        seg("평점평균: 4.00/4.5 백분율: 93.00/100", 60, 180, 220),
    ]
    assert (
        fields(DocumentType.TRANSCRIPT, lines)["gpa"] is None
    )  # two semesters disagree: abstain, as before


def test_label_tolerance_is_substitution_only() -> None:
    assert starts_with_label("총취득학정:104", "총취득학점")
    assert starts_with_label("총취득학점:104", "총취득학점")
    assert not starts_with_label("취득학점:15", "총취득학점")  # a missing syllable is not tolerated
    assert not starts_with_label("총총취득학점", "총취득학점")  # nor an extra one
    assert not starts_with_label("총쉬독학점", "총취득학점")  # two wrong syllables
    assert not starts_with_label("총득점", "총득점")  # labels shorter than four syllables are exact
    assert find_label("xx평정평균3.1/4.5", "평점평균") == 6
    assert find_label("xxxx", "평점평균") == -1
