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

from dataclasses import dataclass

from app.document_intelligence.ocr.models import OCRLine, OCRPage

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
