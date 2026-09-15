"""Field normalization -- separate from extraction and validation.

Extraction decides *where* a value came from. Normalization decides how to
represent a raw OCR string safely. It never invents a value: given an
ambiguous or invalid input it returns None rather than a best guess.
"""

import re
from datetime import date

DATE_RE = re.compile(r"(20\d{2})[.\-/년 ]\s*(\d{1,2})[.\-/월 ]\s*(\d{1,2})")
BUSINESS_NUMBER_RE = re.compile(r"(\d{3})[- ]?(\d{2})[- ]?(\d{5})")
_EDGE_NOISE_RE = re.compile(r"^[\s:：·\-_]+|[\s:：·\-_]+$")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_date(value: str | None) -> str | None:
    """Accepts '2026. 9. 8.', '2026-09-08', '2026/09/08', '2026년 9월 8일'
    (and combinations with stray whitespace). Returns ISO 8601 or None --
    never a guessed/rounded date for invalid or ambiguous input."""
    if not value:
        return None
    match = DATE_RE.search(value)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def normalize_business_number(value: str | None) -> str | None:
    """Normalizes a candidate business registration number to
    'XXX-XX-XXXXX'. Callers are responsible for only passing text that was
    found near a business-number label -- this function does not, by
    itself, decide whether a 10-digit run is contextually a business
    number."""
    if not value:
        return None
    match = BUSINESS_NUMBER_RE.search(value)
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else None


def normalize_text_field(value: str | None) -> str | None:
    """Conservative cleanup for names/organizations: collapse internal
    whitespace and strip stray leading/trailing OCR punctuation. Never
    mutates internal Korean characters or casing."""
    if value is None:
        return None
    collapsed = _WHITESPACE_RE.sub(" ", value).strip()
    trimmed = _EDGE_NOISE_RE.sub("", collapsed).strip()
    return trimmed or None
