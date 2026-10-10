"""Explicit, versioned OCR confusion table and the plausible alternative readings of a value.

CONFUSION_TABLE_VERSION is part of every decision that relies on it. The digit pairs are the standard
look-alike pairs of printed digits (the same pairs the injection suites use, plus a few more);
extending the table is a reviewed code change (see evaluation/harness/calibrate_from_reviews.py,
which lists the confusions seen in human corrections as candidates).
"""

from __future__ import annotations

CONFUSION_TABLE_VERSION = "ocr-confusions-d3-v1"

_PAIRS = [
    ("0", "8"),
    ("1", "7"),
    ("3", "8"),
    ("5", "6"),
    ("6", "8"),
    ("2", "7"),
    ("0", "6"),
    ("4", "9"),
    ("1", "4"),
    ("3", "5"),
]
DIGIT_CONFUSIONS: dict[str, tuple[str, ...]] = {}
for a, b in _PAIRS:
    DIGIT_CONFUSIONS.setdefault(a, ())
    DIGIT_CONFUSIONS.setdefault(b, ())
    DIGIT_CONFUSIONS[a] = (*DIGIT_CONFUSIONS[a], b)
    DIGIT_CONFUSIONS[b] = (*DIGIT_CONFUSIONS[b], a)


def alternative_readings(text: str) -> set[str]:
    """Every string one recogniser error away from `text`: one digit replaced by a confusable
    digit, two adjacent different digits transposed, one digit dropped, one digit added
    (a neighbour repeated). `text` itself is not included; validity is the caller's job."""
    out: set[str] = set()
    for index, char in enumerate(text):
        for substitute in DIGIT_CONFUSIONS.get(char, ()):
            out.add(text[:index] + substitute + text[index + 1 :])
        if char.isdigit():
            out.add(text[:index] + text[index + 1 :])
            out.add(text[: index + 1] + char + text[index + 1 :])
        if (
            index + 1 < len(text)
            and text[index].isdigit()
            and text[index + 1].isdigit()
            and text[index] != text[index + 1]
        ):
            out.add(text[:index] + text[index + 1] + text[index] + text[index + 2 :])
    out.discard(text)
    return out
