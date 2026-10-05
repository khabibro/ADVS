"""Field normalization -- separate from extraction and validation.

Extraction decides *where* a value came from. Normalization decides how to
represent a raw OCR string safely. It never invents a value: given an
ambiguous or invalid input it returns None rather than a best guess.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

DATE_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})(?!\d)")
BUSINESS_NUMBER_RE = re.compile(r"(?<!\d)(\d{3})[- ]?(\d{2})[- ]?(\d{5})(?!\d)")
GPA_RE = re.compile(r"(?<!\d)(\d(?:\.\d{1,3})?)(?:\s*/\s*(\d(?:\.\d{1,3})?))?(?!\d)")
_EDGE_NOISE_RE = re.compile(r"^[\s:：·\-_]+|[\s:：·\-_]+$")
_WHITESPACE_RE = re.compile(r"\s+")

# Characters that render as a hyphen but are not U+002D. NFKC already folds
# the fullwidth forms; these are the ones it leaves alone, and they are what
# recognizers emit when the source used a typographic dash. Apply this only
# inside a numeric field, never to organization names or before range parsing.
_DASH_VARIANTS = "‐‑‒–—―−﹘﹣－"


def normalize_lexical_text(value: str) -> str:
    """Width compatibility only; retain semantic punctuation and raw evidence."""
    return unicodedata.normalize("NFKC", value)


def canonicalize_numeric_text(value: str) -> str:
    """Fold width and dash variants so numeric patterns see plain ASCII.

    This is a character-set normalization only: no digit, sign or separator is
    added, removed or reordered, so a string that does not contain a number
    still does not after this runs.
    """
    folded = normalize_lexical_text(value)
    return "".join("-" if ch in _DASH_VARIANTS else ch for ch in folded)


def normalize_date(value: str | None) -> str | None:
    """Accepts '2026. 9. 8.', '2026-09-08', '2026/09/08', '2026년 9월 8일'
    (and combinations with stray whitespace or typographic dashes). Returns
    ISO 8601 or None -- never a guessed/rounded date for invalid or ambiguous
    input."""
    if not value:
        return None
    matches = list(DATE_RE.finditer(canonicalize_numeric_text(value)))
    # A scalar normalizer must never select one endpoint from a range or
    # choose among multiple dates, even when the dates happen to be equal.
    if len(matches) != 1:
        return None
    match = matches[0]
    remainder = (
        canonicalize_numeric_text(value)[: match.start()]
        + canonicalize_numeric_text(value)[match.end() :]
    )
    if re.search(r"[~∼〜-]|부터|에서", remainder):
        return None
    year, month, day = map(int, match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def split_date_range(value: str | None) -> tuple[str | None, str | None]:
    """Locate two complete dates, then interpret only the text BETWEEN them.

    Numeric dash folding is length-preserving, so the spans also index the
    lexical text. Internal date hyphens cannot be confused with a boundary.
    Unknown, incomplete, reversed, and multi-period ranges abstain.
    """
    if not value:
        return None, None
    lexical = normalize_lexical_text(value)
    matches = list(DATE_RE.finditer(canonicalize_numeric_text(lexical)))
    if len(matches) != 2:
        return None, None
    left, right = matches
    boundary = lexical[left.end() : right.start()].strip().lstrip("일.").strip()
    if boundary not in {"~", "∼", "〜", "-", *_DASH_VARIANTS, "부터", "에서"}:
        return None, None
    start, end = lexical[left.start() : left.end()], lexical[right.start() : right.end()]
    normalized_start, normalized_end = normalize_date(start), normalize_date(end)
    if normalized_start is None or normalized_end is None or normalized_start > normalized_end:
        return None, None
    return start, end


def normalize_business_number(value: str | None) -> str | None:
    """Normalizes a candidate business registration number to
    ten comparison-safe digits. Callers are responsible for only passing text that was
    found near a business-number label -- this function does not, by
    itself, decide whether a 10-digit run is contextually a business
    number."""
    if not value:
        return None
    matches = list(BUSINESS_NUMBER_RE.finditer(canonicalize_numeric_text(value)))
    return "".join(matches[0].groups()) if len(matches) == 1 else None


_BUSINESS_NUMBER_WEIGHTS = (1, 3, 7, 1, 3, 7, 1, 3, 5)


def is_valid_business_number(value: str | None) -> bool:
    """Check digit of a 10-digit 사업자등록번호 (hyphens allowed).

    The commonly published algorithm: weights 1,3,7,1,3,7,1,3,5 on the first
    nine digits, plus floor(d9 * 5 / 10); the check digit is
    (10 - total mod 10) mod 10. Taken from public descriptions, not an official
    specification -- confirm against an official source before relying on it.
    """
    if not value:
        return False
    digits = normalize_business_number(value)
    if digits is None:
        return False
    numbers = [int(character) for character in digits]
    total = sum(
        digit * weight for digit, weight in zip(numbers[:9], _BUSINESS_NUMBER_WEIGHTS, strict=True)
    )
    total += numbers[8] * 5 // 10
    return (10 - total % 10) % 10 == numbers[9]


def normalize_gpa(value: str | None) -> str | None:
    """Returns the GPA numerator as a canonical decimal string.

    The original OCR text remains in ``raw_value``. Values with an explicit
    scale are rejected when the numerator exceeds that scale.
    """
    match = GPA_RE.fullmatch(value.strip()) if value else None
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
    match = GPA_RE.fullmatch(value.strip()) if value else None
    if not match or not match.group(2):
        return None
    try:
        scale = Decimal(match.group(2))
    except InvalidOperation:
        return None
    if scale <= 0 or scale > 10:
        return None
    return format(scale.normalize(), "f")


# Korean/English legal-entity markers that appear at the very start or end
# of a company name and mean nothing beyond "this is a company" -- the same
# company is routinely printed with a different one of these across
# different certificate types (audit F-002: 주식회사 X / (주)X / X(주) /
# ㈜X all named the same company and compared unequal). Longer markers are
# listed before a shorter one they contain (유한책임회사 before 유한회사)
# so the longer, more specific marker is tried first.
LEGAL_ENTITY_MARKERS: tuple[str, ...] = (
    "유한책임회사",
    "주식회사",
    "유한회사",
    "합자회사",
    "합명회사",
    "사단법인",
    "재단법인",
    "(주)",
    "(유)",
    "(사)",
    "(재)",
    "㈜",
    "Co., Ltd.",
    "Co.,Ltd.",
    "Co., Ltd",
    "Co.,Ltd",
    "Inc.",
    "Corp.",
)


def strip_legal_entity_markers(value: str | None) -> str:
    """Remove a legal-entity marker from a name's start or end, as a whole
    token only -- never from the middle, and never a partial match.

    `주원상사` does not start with `주식회사`, and `한주테크` does not end
    with any marker, so neither is altered: this only ever removes a
    marker that is the *entire* leading or trailing token, not merely a
    shared syllable. Safe to apply repeatedly (handles a marker at both
    ends); returns "" for no input rather than None, since this feeds a
    comparison key, not a stored value.
    """
    text = (value or "").strip()
    changed = True
    while changed:
        changed = False
        for marker in LEGAL_ENTITY_MARKERS:
            if text.startswith(marker):
                text = text[len(marker) :].strip()
                changed = True
            elif text.endswith(marker):
                text = text[: -len(marker)].strip()
                changed = True
    return text


def normalize_text_field(value: str | None) -> str | None:
    """Conservative cleanup for names/organizations: collapse internal
    whitespace and strip stray leading/trailing OCR punctuation. Never
    mutates internal Korean characters or casing."""
    if value is None:
        return None
    collapsed = _WHITESPACE_RE.sub(" ", value).strip()
    trimmed = _EDGE_NOISE_RE.sub("", collapsed).strip()
    return trimmed or None
