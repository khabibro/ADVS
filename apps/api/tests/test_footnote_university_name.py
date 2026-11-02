"""A transcript whose issuer line was not read still names its university in a footnote sentence. The name is
only extracted when it is unambiguous, and it is never self-referential. All names are invented."""

from __future__ import annotations

from app.core.domain import DocumentType
from tests.test_phase_c_extraction import fields, seg


def _page(*footnotes: str) -> list:
    lines = [seg("성적증명서", 200, 40), seg("학번: 2020123456", 60, 100, 200)]
    for index, text in enumerate(footnotes):
        lines.append(seg(text, 60, 400 + 30 * index, 420))
    return lines


def test_footnote_names_the_university() -> None:
    got = fields(
        DocumentType.TRANSCRIPT, _page("※다라 대학교에서는 2001학년도부터 평점을 환산합니다.")
    )
    assert got["university_name"] == "다라대학교"


def test_footnote_without_a_space_is_read_too() -> None:
    got = fields(DocumentType.TRANSCRIPT, _page("※마바대학교에서는 성적을 공개하지 않습니다."))
    assert got["university_name"] == "마바대학교"


def test_two_different_names_give_no_answer() -> None:
    got = fields(
        DocumentType.TRANSCRIPT,
        _page("※다라 대학교에서는 환산합니다.", "※마바 대학교에서는 환산합니다."),
    )
    assert got["university_name"] is None


def test_self_reference_names_no_university() -> None:
    got = fields(
        DocumentType.TRANSCRIPT,
        _page("※우리 대학교에서는 환산합니다.", "※본 대학교에서는 환산합니다."),
    )
    assert got["university_name"] is None


def test_the_issuer_line_wins_over_a_footnote() -> None:
    lines = _page("※다라 대학교에서는 환산합니다.") + [seg("사아자대학교총장", 100, 600, 300)]
    assert fields(DocumentType.TRANSCRIPT, lines)["university_name"] == "사아자대학교"


def test_a_sentence_that_only_mentions_a_university_is_not_a_footnote_name() -> None:
    got = fields(
        DocumentType.TRANSCRIPT, _page("이 증명서는 다라대학교의 규정에 따라 발급되었습니다.")
    )
    assert got["university_name"] is None
