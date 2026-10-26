"""Layout-preserving grouping of detected text lines.

A real Korean certificate is not a list of independent lines. ``성  명 :
홍길동`` is one visual row that an OCR detector legitimately reports as
three separate boxes, because the characters are letter-spaced. Collapsing
those boxes into *one* :class:`OCRLine` destroys the only evidence that the
gap between "성" and "명" is the label's own letter-spacing rather than the
boundary between two different fields.

This module keeps both views:

* the individual :class:`OCRLine` segments (each with its own bounding box
  and confidence), and
* a :class:`TextRow` that says "these segments share a baseline".

Everything downstream matches labels against ``TextRow.text`` but attaches
evidence to the *specific segments* the matched value came from.

Grouping is purely geometric and purely horizontal: two segments join a row
only when their vertical spans genuinely overlap. Multi-line body text is
therefore never collapsed, and reading order is still decided by
:mod:`app.document_intelligence.ocr.text_assembly`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage

# Two boxes belong to the same visual row when their vertical spans overlap
# by at least this fraction of the shorter box's height. 0.5 tolerates the
# small baseline differences produced by superscripts, descenders in Latin
# text, and detector jitter, without merging genuinely different lines.
DEFAULT_OVERLAP_RATIO = 0.5


@dataclass(frozen=True)
class TextRow:
    """Detected boxes that share a visual baseline, in left-to-right order."""

    page_number: int
    segments: tuple[OCRLine, ...]

    @property
    def text(self) -> str:
        """Segments joined by a single space -- unless the boxes abut.

        A real gap between two segments is whitespace in the source document, so it
        becomes a space (the label patterns tolerate intra-label spacing). Boxes that
        touch (gap under a quarter of the text height) are one word the detector cut in
        two, so they are joined without a space.
        """
        parts: list[str] = []
        previous: OCRLine | None = None
        for segment in self.segments:
            if not segment.text:
                continue
            if previous is not None:
                parts.append("" if _abuts(previous, segment) else " ")
            parts.append(segment.text)
            previous = segment
        return "".join(parts)

    @property
    def has_geometry(self) -> bool:
        return all(segment.bounding_box is not None for segment in self.segments)


ABUT_GAP_RATIO = 0.25


def _abuts(left: OCRLine, right: OCRLine) -> bool:
    left_box, right_box = left.bounding_box, right.bounding_box
    if left_box is None or right_box is None:
        return False
    gap = right_box.x - (left_box.x + left_box.width)
    return -left_box.height <= gap < ABUT_GAP_RATIO * min(left_box.height, right_box.height)


def _vertical_overlap(left: OCRLine, right: OCRLine) -> float:
    left_box, right_box = left.bounding_box, right.bounding_box
    assert left_box is not None and right_box is not None
    return min(left_box.y + left_box.height, right_box.y + right_box.height) - max(
        left_box.y, right_box.y
    )


def build_rows(page: OCRPage, overlap_ratio: float = DEFAULT_OVERLAP_RATIO) -> list[TextRow]:
    """Group a page's lines into visual rows.

    Lines without geometry (for example a plain-text source) each become
    their own single-segment row, so callers never need a separate
    geometry-free code path.
    """
    if not page.lines:
        return []

    # Lines without geometry (e.g. a plain-text source, or a PDF text line
    # PyMuPDF could not box) each become their own single-segment row. They
    # are kept in their original document position rather than appended, so
    # "label on one line, value on the next" still works when only one of
    # the two carries geometry.
    position = {id(line): index for index, line in enumerate(page.lines)}
    rows: list[tuple[int, TextRow]] = []

    with_geometry = [
        line for line in page.lines if line.bounding_box is not None and line.text.strip()
    ]
    without_geometry = [
        line for line in page.lines if line.bounding_box is None and line.text.strip()
    ]

    if with_geometry:
        ordered = sorted(
            with_geometry,
            key=lambda line: (
                line.bounding_box.y + line.bounding_box.height / 2,  # type: ignore[union-attr]
                line.bounding_box.x,  # type: ignore[union-attr]
            ),
        )
        current: list[OCRLine] = [ordered[0]]
        for line in ordered[1:]:
            anchor = current[-1]
            required = (
                min(anchor.bounding_box.height, line.bounding_box.height)  # type: ignore[union-attr]
                * overlap_ratio
            )
            if _vertical_overlap(anchor, line) >= required:
                current.append(line)
            else:
                segment_run = _left_to_right(current)
                rows.append(
                    (
                        min(position[id(item)] for item in segment_run),
                        TextRow(page.page_number, tuple(segment_run)),
                    )
                )
                current = [line]
        segment_run = _left_to_right(current)
        rows.append(
            (
                min(position[id(item)] for item in segment_run),
                TextRow(page.page_number, tuple(segment_run)),
            )
        )

    rows.extend(
        (position[id(line)], TextRow(page.page_number, (line,))) for line in without_geometry
    )
    rows.sort(key=lambda item: item[0])
    return [row for _, row in rows]


def _left_to_right(lines: list[OCRLine]) -> list[OCRLine]:
    return sorted(lines, key=lambda line: line.bounding_box.x)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Stacked label glyphs fused into one tall box
# ---------------------------------------------------------------------------

_HANGUL_ONLY_RE = re.compile(r"[가-힣]{2,4}")
_LABEL_TAIL_RE = re.compile(r"[가-힣]{1,3}\s*[:：]")
# A glyph column: each character of the fused box occupies a roughly square cell.
_CELL_ASPECT = (0.6, 1.7)
_TAIL_REACH_HEIGHTS = (
    14.0  # how far right of the fused box the label tails may start (cell heights)
)


def split_stacked_label_boxes(lines: list[OCRLine]) -> list[OCRLine]:
    """Undo a detector fusing the first syllables of labels printed one above the other.

    In a two-column header such as ``학   번 : ...`` over ``성   명 : ...`` the label syllables are
    far apart horizontally, so the first syllables of the rows above and below can be detected as
    ONE tall narrow box and read top to bottom ("학성"), while the rest of each label stays with its
    value ("번:...", "명:..."). A box is split into one box per character only when all of these hold:
    it is Hangul only, one glyph wide (every character gets a roughly square cell of the box), and
    each of its n cells has, to its right on the same row, a box that begins with the remainder of
    a label (a few syllables then a colon). Anything else is left untouched.
    """
    boxed = [item for item in lines if item.bounding_box is not None and item.text.strip()]
    if len(boxed) < 3:
        return lines
    out: list[OCRLine] = []
    for item in lines:
        pieces = _split_one(item, boxed)
        out.extend(pieces if pieces is not None else [item])
    return out


def _split_one(item: OCRLine, boxed: list[OCRLine]) -> list[OCRLine] | None:
    box = item.bounding_box
    text = "".join(item.text.split())
    if box is None or not _HANGUL_ONLY_RE.fullmatch(text):
        return None
    n = len(text)
    cell_height = box.height / n
    if not _CELL_ASPECT[0] <= box.width / cell_height <= _CELL_ASPECT[1]:
        return None
    slices: list[BoundingBox] = []
    for index in range(n):
        top = box.y + index * cell_height
        slice_box = BoundingBox(box.x, top, box.width, cell_height)
        centre = top + cell_height / 2
        tails = [
            other
            for other in boxed
            if other is not item
            and other.bounding_box is not None
            and other.bounding_box.x >= box.x + box.width - 0.5 * box.width
            and other.bounding_box.x - (box.x + box.width) <= _TAIL_REACH_HEIGHTS * cell_height
            and other.bounding_box.y <= centre <= other.bounding_box.y + other.bounding_box.height
            and _LABEL_TAIL_RE.match(other.text.strip())
        ]
        if not tails:
            return None
        slices.append(slice_box)
    return [
        replace(item, text=char, bounding_box=slice_box, polygon=None)
        for char, slice_box in zip(text, slices, strict=True)
    ]
