"""Field-shape validation and candidate scoring.

Extraction must reject *impossible* candidates, not merely prefer plausible
ones. A value that cannot be a university name is not a university name,
whatever the label next to it says; the correct outcome is an unresolved
field, because a confidently wrong value is far more dangerous than a
``None`` (it can satisfy an evidence-confidence floor and then propagate
into deterministic verification).

Everything here is conservative and domain-agnostic: it validates the
*shape* of a value against the *semantics* of its field, and it never
repairs, guesses, or fuzzy-matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

# Legal fine print that appears on the same rows as real fields: verification
# instructions, app-store advertisements, QR/original-check notices, and
# internet-issuance footers. Deliberately narrow -- these are exact tokens,
# not fuzzy patterns.
_BOILERPLATE_MARKERS = (
    "www.",
    "http://",
    "https://",
    ".com",
    ".co.kr",
    "qr",
    "원본대조",
    "원본 대조",
    "발급번호",
    "앱스토어",
    "구글플레이",
    "다운로드",
    "다운로드하여",
    "smartphone",
    "특허",
    "internetno",
    "발급일로부터",
)

# Suffixes that make a Korean word a plausible organisation name.
_INSTITUTION_SUFFIXES = (
    "대학교",
    "대학",
    "고등학교",
    "중학교",
    "초등학교",
    "학부",
    "법인",
    "주식회사",
    "(주)",
    "㈜",
    "센터",
    "협회",
    "법인사",
    "지점",
)

# Suffixes that make it a department / major rather than a university.
_DEPARTMENT_SUFFIXES = (
    "학과",
    "학부",
    "전공",
    "과",
    "전공과",
)

_PERSON_NAME_MAX_LEN = 20
_ORGANISATION_MAX_LEN = 40

_STRIP_RE = re.compile(r"^[\s:：·\-_]+|[\s:：·\-_]+$")
_COLON_SPLIT_RE = re.compile(r"[:：﹕꞉︓]")


class ValueKind(StrEnum):
    """Semantic category of a canonical field, used to validate candidates."""

    PERSON_NAME = "PERSON_NAME"
    ORGANISATION = "ORGANISATION"
    INSTITUTION = "INSTITUTION"
    DEPARTMENT = "DEPARTMENT"
    FREE_TEXT = "FREE_TEXT"


# Central field -> kind map. Kept here (rather than inside each extractor) so
# the vocabulary stays in one place and adding a field cannot silently skip
# validation.
FIELD_KINDS: dict[str, ValueKind] = {
    "applicant_name": ValueKind.PERSON_NAME,
    "representative_name": ValueKind.PERSON_NAME,
    "student_name": ValueKind.PERSON_NAME,
    "company_name": ValueKind.ORGANISATION,
    "workplace_name": ValueKind.ORGANISATION,
    "university_name": ValueKind.INSTITUTION,
    "department": ValueKind.DEPARTMENT,
    "position": ValueKind.FREE_TEXT,
    "business_address": ValueKind.FREE_TEXT,
    "business_type": ValueKind.FREE_TEXT,
    "business_item": ValueKind.FREE_TEXT,
    "certificate_number": ValueKind.FREE_TEXT,
}


def kind_for(field_name: str) -> ValueKind:
    return FIELD_KINDS.get(field_name, ValueKind.FREE_TEXT)


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def looks_like_boilerplate(value: str) -> bool:
    """True when the text is document chrome rather than a field value."""
    lowered = compact(value).lower()
    return any(marker in lowered for marker in _BOILERPLATE_MARKERS)


def is_person_name(value: str) -> bool:
    stripped = compact(value)
    if not stripped or looks_like_boilerplate(stripped):
        return False
    if len(stripped) > _PERSON_NAME_MAX_LEN:
        return False
    if ":" in stripped:
        return False
    if sum(character.isdigit() for character in stripped) > 2:
        return False
    return any("가" <= character <= "힣" for character in stripped)


def _ends_with_any(value: str, suffixes: tuple[str, ...]) -> bool:
    return any(value.endswith(suffix) for suffix in suffixes)


def is_institution(value: str) -> bool:
    """A university/school name.

    Requires a recognised institution suffix. This is why "경 '북 대 학 교
    총" yields no candidate for ``university_name``: the row's tail is
    "총", which is not an institution, and the row is therefore rejected
    rather than accepted and then fuzzy-matched.
    """
    stripped = compact(value)
    if not stripped or looks_like_boilerplate(stripped):
        return False
    if len(stripped) > _ORGANISATION_MAX_LEN:
        return False
    return _ends_with_any(stripped, _INSTITUTION_SUFFIXES)


def is_organisation(value: str) -> bool:
    """A company / workplace name.

    Must be short enough to be a name, must not be legal fine print, and
    must not simply be a numeric identifier.
    """
    stripped = compact(value)
    if not stripped or looks_like_boilerplate(stripped):
        return False
    if len(stripped) > _ORGANISATION_MAX_LEN:
        return False
    if ":" in stripped:
        return False
    if sum(character.isdigit() for character in stripped) > 4:
        return False
    return any("가" <= character <= "힣" for character in stripped)


def is_department(value: str) -> bool:
    stripped = compact(value)
    if not stripped or looks_like_boilerplate(stripped):
        return False
    if len(stripped) > _ORGANISATION_MAX_LEN:
        return False
    return _ends_with_any(stripped, _DEPARTMENT_SUFFIXES)


def is_free_text(value: str) -> bool:
    stripped = compact(value)
    if not stripped or looks_like_boilerplate(stripped):
        return False
    if ":" in stripped:
        return False
    return len(stripped) <= _ORGANISATION_MAX_LEN


_VALIDATORS = {
    ValueKind.PERSON_NAME: is_person_name,
    ValueKind.ORGANISATION: is_organisation,
    ValueKind.INSTITUTION: is_institution,
    ValueKind.DEPARTMENT: is_department,
    ValueKind.FREE_TEXT: is_free_text,
}


def is_valid_value(field_name: str, value: str) -> bool:
    """Extraction-time candidate validation.

    This is *not* submission verification. It only asks "could this string
    plausibly be a value of this field", so that an impossible capture is
    turned into an unresolved field instead of a confident wrong one.
    """
    return _VALIDATORS[kind_for(field_name)](value)


@dataclass(frozen=True)
class CandidateScore:
    total: float
    reasons: tuple[str, ...]


def score_candidate(
    *,
    field_name: str,
    value: str,
    has_explicit_separator: bool,
    label_is_exact: bool,
    row_index: int,
) -> CandidateScore:
    """Rank a candidate. Higher is better; invalid candidates score 0.

    Signals, in descending weight:

    1. shape validity against the field's semantics (hard gate)
    2. explicit ``label: value`` separator (the strongest textual signal)
    3. the label was matched on its own rather than inside a longer word
    4. a shorter value, which is what names and identifiers look like
    5. an earlier row, which on a form is the primary field before any
       secondary (e.g. 주전공 before 복수전공)
    """
    if not is_valid_value(field_name, value):
        return CandidateScore(0.0, ("invalid_shape",))

    reasons: list[str] = ["valid_shape"]
    total = 100.0
    if has_explicit_separator:
        total += 20.0
        reasons.append("explicit_separator")
    else:
        total += 6.0
    if label_is_exact:
        total += 8.0
        reasons.append("exact_label")
    length_penalty = min(len(compact(value)) / 4.0, 25.0)
    total -= length_penalty
    if length_penalty > 5.0:
        reasons.append("long_value")
    total -= min(row_index * 0.5, 5.0)
    return CandidateScore(total, tuple(reasons))
