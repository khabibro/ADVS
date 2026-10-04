"""Section inference from OCR geometry.

A repeated label in a long document usually means the same field printed once
per block, not one field with several candidate values. Two real transcripts
behave exactly this way: one prints a grade-point average under each of five
bracketed semester headings, the other under a header/value summary table.
Pooling those into a single candidate set is what forces abstention; scoping
each occurrence to the block that owns it is what makes the structure legible
to a reviewer.

Sections are inferred from geometry alone:

* an **explicit heading** — a line bracketed on both sides (``<<...>>``) — which
  is a common typographic convention for a block heading, and
* a **vertical gap** markedly larger than the page's median row pitch.

No list of institution names, document titles or field names is consulted, and
nothing here is specific to transcripts: any document with large vertical gaps
gets sections.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.document_intelligence.ocr.models import BoundingBox

# A vertical gap larger than this multiple of the median inter-row pitch starts
# a new section. 2.0 is deliberately conservative: ordinary line spacing sits
# near 1.0, and block separation is visibly larger.
SECTION_GAP_RATIO = 2.0

# Blocks shorter than this many rows are not treated as sections; they are
# more likely a heading plus its single line than a real block.
MIN_SECTION_ROWS = 2

# An explicit heading is a short line fully wrapped in matching brackets.
# An explicit heading is a short line fully wrapped in double angle brackets or
# square brackets. A single parenthetical is deliberately NOT accepted: on a
# Korean certificate "(법인사업자)" is a sub-caption inside a block, and treating
# it as a block heading split one form into three phantom sections. Only a
# delimiter that is not used for parenthetical qualification qualifies here.
_HEADING_RE = re.compile(r"^(<<.+>>|\[.+\])$")
_MAX_HEADING_CHARS = 40


@dataclass(frozen=True)
class Section:
    """A contiguous vertical block of rows."""

    index: int
    first_row: int
    last_row: int
    heading: str | None = None
    explicit: bool = False

    def contains(self, row_index: int) -> bool:
        return self.first_row <= row_index <= self.last_row

    @property
    def row_count(self) -> int:
        return self.last_row - self.first_row + 1


@dataclass(frozen=True)
class SectionModel:
    sections: tuple[Section, ...]
    total_rows: int

    def section_for(self, row_index: int) -> Section | None:
        for section in self.sections:
            if section.contains(row_index):
                return section
        return None

    def section_index_for(self, row_index: int) -> int | None:
        section = self.section_for(row_index)
        return None if section is None else section.index

    def repeated_across_sections(self, row_indices: Sequence[int]) -> bool:
        """True when the given rows fall in more than one distinct section."""
        found = {
            index
            for index in (self.section_index_for(row) for row in row_indices)
            if index is not None
        }
        return len(found) > 1


def _row_box(boxes: Sequence[BoundingBox | None]) -> tuple[float, float] | None:
    """Vertical centre and height of a row, from its boxes."""
    present = [box for box in boxes if box is not None]
    if not present:
        return None
    top = min(box.y for box in present)
    bottom = max(box.y + box.height for box in present)
    return (top + bottom) / 2, max(bottom - top, 1.0)


def _median(values: Sequence[float]) -> float:
    if not values:
        return 1.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _is_heading(text: str) -> bool:
    compact = text.strip()
    if not compact or len(compact) > _MAX_HEADING_CHARS:
        return False
    return bool(_HEADING_RE.match(compact))


def infer_sections(
    rows: Sequence[tuple[str, Sequence[BoundingBox | None]]],
) -> SectionModel:
    """Partition rows into sections.

    `rows` is (row_text, segment_boxes) in reading order for one page.
    """
    total = len(rows)
    if total == 0:
        return SectionModel((), 0)

    geometry = [_row_box(boxes) for _text, boxes in rows]
    # Row pitch is the distance between consecutive row centres. The median
    # pitch is the page's normal line spacing, and the section threshold is a
    # multiple of it, so the threshold adapts to render scale and font size
    # instead of carrying an absolute pixel constant.
    pitches: list[float] = []
    for previous, current in zip(geometry, geometry[1:], strict=False):
        if previous is None or current is None:
            continue
        pitch = current[0] - previous[0]
        if pitch > 0:
            pitches.append(pitch)
    median_pitch = _median(pitches) if pitches else 1.0
    threshold = SECTION_GAP_RATIO * median_pitch

    cuts: list[tuple[int, str | None, bool]] = []
    for index in range(1, total):
        previous, current = geometry[index - 1], geometry[index]
        heading_text: str | None = None
        explicit = False
        if previous is not None and current is not None:
            if current[0] - previous[0] > threshold:
                cuts.append((index, None, False))
                continue
        if _is_heading(rows[index - 1][0]):
            heading_text = rows[index - 1][0].strip()
            explicit = True
            cuts.append((index, heading_text, True))

    if not cuts:
        return SectionModel((Section(0, 0, total - 1),), total)

    sections: list[Section] = []
    # A leading heading with no content before it starts section 0.
    start = 0
    pending_heading: str | None = None
    pending_explicit = False
    for cut_index, heading, explicit in cuts:
        if cut_index - start < MIN_SECTION_ROWS and start != 0:
            continue
        sections.append(
            Section(len(sections), start, cut_index - 1, pending_heading, pending_explicit)
        )
        start = cut_index
        pending_heading = heading
        pending_explicit = explicit
    sections.append(Section(len(sections), start, total - 1, pending_heading, pending_explicit))

    return SectionModel(tuple(sections), total)
