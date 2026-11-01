"""One definition of "the same company" for the comparison key used by the acceptance policy and by the
submission rules.

Notation differences that do not change the company: the legal form (주식회사 / (주) / ㈜), spaces, and a
parenthesised text with Latin letters and no Hangul printed beside the name (a translation or abbreviation that one
certificate prints and another leaves out). A shorter name (a workplace name on the insurance certificate) also
agrees when it is the start of the longer one *and* both documents carry the same business number that passes the
check digit. Nothing else is tolerated: no similarity measure, no edit distance."""

from __future__ import annotations

import re
import unicodedata

from app.document_intelligence.normalization.field_normalizer import (
    is_valid_business_number,
    strip_legal_entity_markers,
)

_LATIN_PAREN_RE = re.compile(r"\([^()가-힣]*[A-Za-z][^()가-힣]*\)")
MIN_PREFIX_NAME_CHARS = 3


def company_key(value: str) -> str:
    text = _LATIN_PAREN_RE.sub("", unicodedata.normalize("NFKC", value))
    return "".join(strip_legal_entity_markers(text).split())


def _digits(value: str | None) -> str:
    return "".join(ch for ch in value or "" if ch.isdigit())


def same_registered_business(left_number: str | None, right_number: str | None) -> bool:
    digits = _digits(left_number)
    return bool(digits) and digits == _digits(right_number) and is_valid_business_number(digits)


def company_names_agree(
    left_key: str, right_key: str, left_number: str | None, right_number: str | None
) -> bool:
    """Equal keys, or the shorter key starts the longer one while both documents show the same valid number."""
    if left_key == right_key:
        return True
    short, long_ = sorted((left_key, right_key), key=len)
    return (
        len(short) >= MIN_PREFIX_NAME_CHARS
        and long_.startswith(short)
        and same_registered_business(left_number, right_number)
    )
