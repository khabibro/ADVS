"""Tolerance of printed label text to a misread syllable.

A recogniser sometimes reads one syllable of a label wrongly ("총 취득학점" as "총 취득학정"). Labels are
used only to *locate* a line or a value; the value is still parsed and checked as before and goes through
the acceptance policy. The tolerance is deliberately narrow:

* substitutions only: a missing or an extra syllable never matches, so "취득학점" (one semester) is never
  mistaken for "총취득학점" (all semesters);
* at most one wrong syllable, and only in labels of four or more syllables.
"""

from __future__ import annotations

LABEL_TOLERANCE_VERSION = "label-tolerance-v1"
MIN_LABEL_LENGTH = 4
MAX_SUBSTITUTIONS = 1


def _mismatches(window: str, label: str) -> int:
    return sum(1 for seen, expected in zip(window, label, strict=True) if seen != expected)


def starts_with_label(compact_text: str, label: str) -> bool:
    """`compact_text` (no spaces) begins with `label`, allowing one misread syllable."""
    if len(label) < MIN_LABEL_LENGTH or len(compact_text) < len(label):
        return False
    return _mismatches(compact_text[: len(label)], label) <= MAX_SUBSTITUTIONS


def find_label(compact_text: str, label: str) -> int:
    """Index just after the first occurrence of `label` in `compact_text` (one misread syllable
    allowed, exact matches preferred), or -1."""
    exact = compact_text.find(label)
    if exact >= 0:
        return exact + len(label)
    if len(label) < MIN_LABEL_LENGTH:
        return -1
    for start in range(len(compact_text) - len(label) + 1):
        if _mismatches(compact_text[start : start + len(label)], label) <= MAX_SUBSTITUTIONS:
            return start + len(label)
    return -1
