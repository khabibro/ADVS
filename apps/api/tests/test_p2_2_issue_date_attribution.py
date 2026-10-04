"""Regression tests for P2.2: issue-date attribution when the issuance block
carries prose.

The defect these cover: a certificate whose issuance block contains a sentence
that happens to include a date-label word ("issued on") lost its issue date
entirely, even though the date had been read correctly and every other
safety guard had passed. The field went missing rather than wrong, so this was
a false negative, not a safety failure.

These tests pin both directions. The false negative must stay fixed, and the
guard the change must NOT weaken -- a genuine unfulfilled issue-date *label*
still suppressing the inferred date -- must keep working.
"""

from __future__ import annotations

import pytest

from app.document_intelligence.extraction.base import (
    _LABEL_ROW_MAX_CHARS,
    _row_states_a_label,
)
from app.document_intelligence.extraction.social_insurance_payment import (
    SocialInsurancePaymentCertificateExtractor,
)
from app.document_intelligence.extraction.transcript import TranscriptExtractor

# A social insurance payment certificate whose issuance block states its
# purpose in prose immediately above the bare date. "발급일" appears inside the
# sentence as ordinary Korean, not as a field label. No document values from
# the private corpus appear here; the text is a synthetic shape equivalent.
PROSE_ISSUANCE_BLOCK = (
    "4대 사회보험료 완납증명서\n"
    "발급번호 고용보험료 산재보험료\n"
    "발급기준 사업장관리번호 법인등록번호 사업자등록번호\n"
    "사업장명 예시 주식회사\n"
    "사업자등록번호 111-22-33333\n"
    "2024년 05월 01일\n"
    "신청인: 예시\n"
    "근로복지공단 귀하\n"
    "2024년 05월 01일\n"
    "근로복지공단"
)

# Same document, but the sentence above the date is removed, leaving a bare
# issuance block. Used to show the prose is what made the difference.
PROSE_SENTENCE = (
    "완납 증명원 발급일 현재 징수유예액을 제외하고는 체납액이 없음을 "
    "증명하여 주시기 바랍니다"
)


def _issue_date(text: str) -> str | None:
    fields = SocialInsurancePaymentCertificateExtractor().extract(text)
    return fields[2].normalized_value


def test_prose_containing_a_date_label_word_does_not_suppress_the_issue_date() -> None:
    """The regression itself: prose is not an unfulfilled label field."""
    text = PROSE_ISSUANCE_BLOCK.replace(
        "2024년 05월 01일\n신청인", f"{PROSE_SENTENCE}\n2024년 05월 01일\n신청인", 1
    )
    assert _issue_date(text) == "2024-05-01"


def test_bare_issuance_block_without_prose_still_resolves() -> None:
    """Without the prose the same document always resolved; it must still."""
    assert _issue_date(PROSE_ISSUANCE_BLOCK) == "2024-05-01"


def test_a_real_label_row_wins_over_the_bare_date_path() -> None:
    """When a genuine issue-date label owns the next row, the labelled path
    supplies the value and the bare-date inference is not reached at all."""
    text = PROSE_ISSUANCE_BLOCK.replace(
        "2024년 05월 01일\n신청인", "발급일\n2024년 05월 01일\n신청인", 1
    )
    fields = SocialInsurancePaymentCertificateExtractor().extract(text)
    assert fields[2].normalized_value == "2024-05-01"
    assert fields[2].extraction_method == "regex_date"


def test_a_real_unfulfilled_issue_date_label_still_suppresses_inference() -> None:
    """The guard this change must not weaken.

    A row that genuinely *is* an issue-date label, whose own value row is
    unreadable, means evidence was lost locally. Falling back to a bare date
    there would mask that loss, so the field must stay unresolved.
    """
    text = (
        "4대 사회보험료 완납증명서\n"
        "발급번호 고용보험료 산재보험료\n"
        "발급기준 사업장관리번호 법인등록번호 사업자등록번호\n"
        "사업장명 예시 주식회사\n"
        "사업자등록번호 111-22-33333\n"
        "발급일\n"
        "판독불가\n"
        "2024년 05월 01일\n"
        "근로복지공단 귀하\n"
    )
    assert _issue_date(text) is None


def test_a_real_unresolved_label_with_a_trailing_colon_still_suppresses() -> None:
    """A label printed with its colon and no usable value is still a label."""
    text = (
        "4대 사회보험료 완납증명서\n"
        "발급번호 고용보험료 산재보험료\n"
        "발급기준 사업장관리번호 법인등록번호 사업자등록번호\n"
        "사업장명 예시 주식회사\n"
        "사업자등록번호 111-22-33333\n"
        "발급일:\n"
        "판독불가\n"
        "2024년 05월 01일\n"
        "근로복지공단 귀하\n"
    )
    assert _issue_date(text) is None


def test_ambiguity_between_two_bare_dates_still_refuses() -> None:
    """Two different bare dates remain fatal; the change is not a relaxation
    of the ambiguity guard."""
    text = PROSE_ISSUANCE_BLOCK.replace("2024년 05월 01일\n근로복지공단", "2025년 11월 09일\n근로복지공단")
    assert _issue_date(text) is None


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ("발급일", True),
        ("발급일:", True),
        ("성명", True),
        ("사업자등록번호(법인등록번호)", True),
        ("  발급일  ", True),
        (PROSE_SENTENCE, False),
        ("", False),
        ("2024년 05월 01일", False),
        ("성명 홍길동", True),
    ],
)
def test_row_states_a_label(row: str, expected: bool) -> None:
    assert _row_states_a_label(row) is expected


def test_label_row_bound_is_above_the_longest_real_label() -> None:
    """The bound must clear a seven-syllable label plus a qualifier, or real
    labels would be misread as prose and the guard would silently stop
    working."""
    longest_real_label = "사업자등록번호(법인등록번호)"
    assert len(longest_real_label) < _LABEL_ROW_MAX_CHARS
    assert _row_states_a_label(longest_real_label) is True


def test_a_transcript_with_no_issuance_block_still_yields_no_issue_date() -> None:
    """A bare date with no issuer below it is body content, not an issuance
    block. This is the abstention the change must not weaken."""
    text = (
        "성적증명서\n"
        "성명 홍길동\n"
        "학번 20260001\n"
        "입학일 2026/03/02\n"
        "2012 년 8 월 16 일\n"
        "교양 교양학문"
    )
    fields = TranscriptExtractor().extract(text)
    assert fields[3].normalized_value is None


def test_two_different_bare_dates_in_a_transcript_still_refuse() -> None:
    """The ambiguity guard is untouched: disagreeing bare dates stay fatal."""
    text = (
        "성적증명서\n"
        "성명 홍길동\n"
        "학번 20260001\n"
        "2012 년 8 월 16 일\n"
        "2013 년 9 월 17 일\n"
        "관동대학교 총장"
    )
    fields = TranscriptExtractor().extract(text)
    assert fields[3].normalized_value is None
