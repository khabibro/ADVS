"""Is the document's type *strongly established* by what OCR read?

Auto-acceptance removes the human step that used to catch a document of the wrong type, so
an OCR-read document must prove its type before any of its fields can be trusted:

* a **clean title**: the supported title is read inside one visual row and nothing unexplained
  sits immediately before it on that row; or
* **two independent identifier-level signals** (title or document-specific labels) agree.

A garbled qualifier before a supported title ("지방새 납세증명서", "지빙세 …", "X방세 …") is
the signature of a look-alike document (a local-tax certificate is not the national-tax
certificate) whose qualifier OCR damaged. Near-matches of the look-alike qualifiers are
detected against an *explicit* table of OCR glyph confusions -- never a similarity score -- and
make the document UNKNOWN. Embedded PDF text is exact and is not gated.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import (
    IDENTIFIER,
    SIGNALS,
    TITLE,
    UNSUPPORTED_LOOK_ALIKE_TITLES,
)
from app.document_intelligence.ocr.layout import build_rows
from app.document_intelligence.ocr.models import OCRLine, OCRPage

# Qualifiers that turn a supported title into a different document (derived from the Phase B
# look-alike table: 지방세납세증명서, 휴학증명서, 졸업예정증명서).
LOOKALIKE_QUALIFIERS: tuple[str, ...] = tuple(
    sorted(
        {
            title.removesuffix("납세증명서").removesuffix("증명서")
            for title in UNSUPPORTED_LOOK_ALIKE_TITLES
        }
    )
)

# Explicit OCR glyph-confusion table (visually similar Hangul syllables a recogniser swaps).
OCR_CONFUSIONS: dict[str, tuple[str, ...]] = {
    "지": ("저", "치", "시", "자"),
    "방": ("빙", "밤", "발", "항"),
    "세": ("새", "셰", "서", "씨"),
    "휴": ("후", "흐", "휵", "훠"),
    "학": ("힉", "확", "탁", "핵"),
    "졸": ("줄", "출", "촐"),
    "업": ("엄", "얼", "엽", "섭"),
    "예": ("에", "여", "애", "례"),
    "정": ("청", "점", "장", "경"),
}

# Words that legitimately precede a supported title on its row.
BENIGN_PREFIXES: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE: ("국세",),
    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE: ("4대", "사회", "고용", "산재"),
}

_BRACKETED = re.compile(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}")
_HANGUL = re.compile(r"[가-힣]")


@dataclass(frozen=True)
class TitleAssessment:
    established: bool
    reason: str | None = None
    near_match: str | None = None  # the look-alike qualifier the row's prefix nearly matches

    def to_dict(self) -> dict[str, object]:
        return {
            "established": self.established,
            "reason": self.reason,
            "near_match": self.near_match,
        }


def _squash(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).split())


def _char_matches(read: str, expected: str) -> bool:
    if read == expected:
        return True
    if read in OCR_CONFUSIONS.get(expected, ()):
        return True
    return _HANGUL.match(read) is None  # a non-Hangul glyph where a syllable belongs: misread


def _near(window: str, qualifier: str) -> bool:
    """One recogniser error away from `qualifier`: a table confusion / non-Hangul glyph in one
    position, or exactly one syllable dropped. An exact match is not a near-match."""
    if window == qualifier:
        return False
    if len(window) == len(qualifier):
        diffs = [(a, b) for a, b in zip(window, qualifier, strict=True) if a != b]
        return len(diffs) == 1 and _char_matches(diffs[0][0], diffs[0][1])
    if len(window) == len(qualifier) - 1:
        return any(qualifier[:i] + qualifier[i + 1 :] == window for i in range(len(qualifier)))
    return False


def _near_lookalike(prefix: str) -> str | None:
    for qualifier in LOOKALIKE_QUALIFIERS:
        if prefix.endswith(qualifier):
            continue  # exact: the look-alike title table handles it
        for size in (len(qualifier) - 1, len(qualifier)):
            if size >= 1 and len(prefix) >= size and _near(prefix[-size:], qualifier):
                return qualifier
    return None


def _titles(document_type: DocumentType) -> list[str]:
    return [
        _squash(signal.text) for signal in SIGNALS.get(document_type, []) if signal.weight >= TITLE
    ]


ADJACENT_GAP_RATIO = 2.0  # a qualifier box touches or nearly touches the title box


def _adjacent_prefix(segments: list[OCRLine], title: str) -> str | None:
    """The text that sits *immediately* before `title` on its row: the part of the first title
    box before the title, plus the boxes directly to its left while the gap between neighbouring
    boxes stays within about two text heights. A field label further left on the same row
    ("발 급 번 호 ... 완납 증명원") is not part of the title."""
    texts = [_squash(item.text) for item in segments]
    joined = "".join(texts)
    start = joined.find(title)
    if start < 0:
        return None
    offset = 0
    first = 0
    for index, text in enumerate(texts):
        if start < offset + len(text) or (not text and start == offset):
            first = index
            break
        offset += len(text)
    prefix = texts[first][: start - offset]
    for index in range(first - 1, -1, -1):
        right, left = segments[index + 1].bounding_box, segments[index].bounding_box
        if right is None or left is None:
            break
        gap = right.x - (left.x + left.width)
        if gap > ADJACENT_GAP_RATIO * max(left.height, right.height):
            break
        prefix = texts[index] + prefix
    return prefix


def assess_title(
    pages: list[OCRPage], document_type: DocumentType, evidence: list[str]
) -> TitleAssessment:
    """`evidence` = the classifier's matched signal texts for `document_type`."""
    titles = _titles(document_type)
    for page in pages:
        for row in build_rows(page):
            segments = [item for item in row.segments if item.text.strip()]
            for title in titles:
                raw_prefix = _adjacent_prefix(segments, title)
                if raw_prefix is None:
                    continue
                prefix = _squash(_BRACKETED.sub("", raw_prefix))
                near = _near_lookalike(prefix)
                if near:
                    return TitleAssessment(False, "LOOKALIKE_QUALIFIER_NEAR_MATCH", near)
                hangul = "".join(_HANGUL.findall(prefix))
                if not hangul or any(
                    hangul.endswith(word) for word in BENIGN_PREFIXES.get(document_type, ())
                ):
                    return TitleAssessment(True)
                return TitleAssessment(False, "UNEXPLAINED_CHARACTERS_BEFORE_TITLE")
    # no clean in-row title: two independent identifier-level signals may still establish it
    strong = [
        signal
        for signal in SIGNALS.get(document_type, [])
        if signal.weight >= IDENTIFIER and signal.text in evidence
    ]
    if len(strong) >= 2:
        return TitleAssessment(True)
    return TitleAssessment(False, "TITLE_NOT_CLEAN_AND_NO_SECOND_SIGNAL")
