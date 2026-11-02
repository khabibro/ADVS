"""The enrolment certificate recognised by its body labels when its title is damaged.

The enrolment layout is shared with the certificates of other student statuses (휴학, 졸업, 수료, 제적), whose
labels are the same, so the body alone never decides: any word of those statuses anywhere on the document rules
the enrolment certificate out, a document carrying transcript labels is not one, and the attestation of an
official certificate must be there. What remains must print the enrolment word, the year of study (not the
"학년도" of a transcript's semester headings) and the admission date or the affiliation.
"""

from __future__ import annotations

import re

#: Words of the statuses that share the enrolment layout. One anywhere on the document: never an enrolment
#: certificate by its body.
OTHER_STATUS_WORDS: tuple[str, ...] = ("휴학", "졸업", "수료", "제적")
#: Labels of a transcript (a transcript prints the admission date and the semester headings too).
_TRANSCRIPT_WORDS: tuple[str, ...] = ("평점평균", "취득학점", "총평점", "성적증명서")
_YEAR_OF_STUDY = re.compile(r"학년(?!도)")
_ATTESTATION = "증명합니다"

BODY_LABELS_EVIDENCE: tuple[str, ...] = ("재학", "학년", "입학일자|소속")


def enrolment_body_labels(squashed_text: str) -> bool:
    """True when the whole document, squashed of spaces, reads as an enrolment certificate by its body."""
    if any(word in squashed_text for word in OTHER_STATUS_WORDS):
        return False
    if any(word in squashed_text for word in _TRANSCRIPT_WORDS):
        return False
    return (
        "재학" in squashed_text
        and _YEAR_OF_STUDY.search(squashed_text) is not None
        and ("입학일자" in squashed_text or "소속" in squashed_text)
        and _ATTESTATION in squashed_text
    )
