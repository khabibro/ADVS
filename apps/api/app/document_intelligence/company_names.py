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
    LEGAL_ENTITY_MARKERS,
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


# ---- aliases -------------------------------------------------------------------------------------------------
# Every name form a certificate prints is an alias of the company: the Korean name and the Latin name in brackets
# ("(주)가나다상사 (Ganada 21)" -> 가나다상사 and ganada21). Aliases are compared after NFKC, case folding, removing
# the legal-form markers at either end and removing every space and punctuation mark. Nothing is transliterated
# and nothing is similar-by-distance: two names are the same company only if some alias is exactly equal.
_MARKERS_FOLDED = tuple(sorted({m.casefold() for m in LEGAL_ENTITY_MARKERS}, key=len, reverse=True))
_MIN_ALIAS_CHARS = 2


def _alias_key(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold().strip()
    changed = True
    while changed:
        changed = False
        for marker in _MARKERS_FOLDED:
            if folded.startswith(marker):
                folded, changed = folded[len(marker) :].strip(), True
            elif folded.endswith(marker):
                folded, changed = folded[: -len(marker)].strip(), True
    return "".join(ch for ch in folded if ch.isalnum())


def company_aliases(value: str | None) -> frozenset[str]:
    """The alias keys of a printed or typed company name (empty when nothing usable is left)."""
    if not value or not value.strip():
        return frozenset()
    text = unicodedata.normalize("NFKC", value)
    keys = {_alias_key(text)}
    keys.add(_alias_key(_LATIN_PAREN_RE.sub("", text)))
    for group in _LATIN_PAREN_RE.findall(text):
        keys.add(_alias_key(group[1:-1]))
    return frozenset(key for key in keys if len(key) >= _MIN_ALIAS_CHARS)


def alias_pool(values: list[str | None]) -> frozenset[str]:
    pool: set[str] = set()
    for value in values:
        pool |= company_aliases(value)
    return frozenset(pool)


def typed_name_matches(typed: str | None, pool: frozenset[str]) -> bool:
    """True when the typed company name equals some alias printed on the documents."""
    return bool(company_aliases(typed) & pool)
