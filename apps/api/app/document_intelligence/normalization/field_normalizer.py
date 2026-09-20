"""Field normalization -- separate from extraction and validation.

Extraction decides *where* a value came from. Normalization decides how to
represent a raw OCR string safely. It never invents a value: given an
ambiguous or invalid input it returns None rather than a best guess.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

DATE_RE = re.compile(r"(20\d{2})[.\-/년 ]\s*(\d{1,2})[.\-/월 ]\s*(\d{1,2})")
BUSINESS_NUMBER_RE = re.compile(r"(?<!\d)(\d{3})[- ]?(\d{2})[- ]?(\d{5})(?!\d)")
GPA_RE = re.compile(r"(?<!\d)(\d(?:\.\d{1,3})?)(?:\s*/\s*(\d(?:\.\d{1,3})?))?(?!\d)")
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
    ten comparison-safe digits. Callers are responsible for only passing text that was
    found near a business-number label -- this function does not, by
    itself, decide whether a 10-digit run is contextually a business
    number."""
    if not value:
        return None
    match = BUSINESS_NUMBER_RE.search(value)
    return "".join(match.groups()) if match else None


def normalize_gpa(value: str | None) -> str | None:
    """Returns the GPA numerator as a canonical decimal string.

    The original OCR text remains in ``raw_value``. Values with an explicit
    scale are rejected when the numerator exceeds that scale.
    """
    match = GPA_RE.search(value) if value else None
    if not match:
        return None
    try:
        score = Decimal(match.group(1))
        scale = Decimal(match.group(2)) if match.group(2) else None
    except InvalidOperation:
        return None
    if score < 0 or score > 10 or (scale is not None and (scale <= 0 or score > scale)):
        return None
    return format(score.normalize(), "f")


def normalize_gpa_scale(value: str | None) -> str | None:
    """Returns an explicit GPA scale as a canonical decimal string."""
    match = GPA_RE.search(value) if value else None
    if not match or not match.group(2):
        return None
    try:
        scale = Decimal(match.group(2))
    except InvalidOperation:
        return None
    if scale <= 0 or scale > 10:
        return None
    return format(scale.normalize(), "f")


def normalize_text_field(value: str | None) -> str | None:
    """Conservative cleanup for names/organizations: collapse internal
    whitespace and strip stray leading/trailing OCR punctuation. Never
    mutates internal Korean characters or casing."""
    if value is None:
        return None
    collapsed = _WHITESPACE_RE.sub(" ", value).strip()
    trimmed = _EDGE_NOISE_RE.sub("", collapsed).strip()
    return trimmed or None
