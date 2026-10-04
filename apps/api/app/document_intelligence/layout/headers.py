"""Header row / value row pairing.

A summary table prints its column headings in one row and the corresponding
values in the next, with columns aligned but each heading and each value in
its own box. Same-row geometry cannot pair them, because they are not on the
same baseline; a label-only association finds a heading and no value, and the
field is lost even though the document states it clearly.

Detection is geometric and conservative:

* the candidate header row has several short segments,
* the row beneath it has segments whose horizontal centres align with the
  header segments to within a tolerance, and
* the header segments do not themselves look like values.

When all three hold, the pairing is reported as structure. It does not decide
that any particular header names any particular field; that remains the
extractor's job, under the usual shape validation and abstention rules.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.document_intelligence.ocr.models import BoundingBox

# Centres must agree to within this multiple of the median header segment
# width for a header/value pairing to be accepted.
ALIGNMENT_TOLERANCE_RATIO = 0.75

# A header row must have at least this many segments. Two columns is already
# handled by same-row association, so the multi-segment rule starts at three.
MIN_HEADER_SEGMENTS = 3

# A segment longer than this multiple of the median width in its row is a
# value, not a heading.
MAX_HEADING_WIDTH_RATIO = 2.5


@dataclass(frozen=True)
class HeaderValuePair:
    """One heading segment paired with the value box beneath it."""

    header_row: int
    value_row: int
    header_index: int
    value_index: int
    alignment_error: float

    @property
    def aligned(self) -> bool:
        return True


@dataclass(frozen=True)
class HeaderValueModel:
    """All header/value pairs found on one page."""

    pairs: tuple[HeaderValuePair, ...]

    def value_for(self, header_row: int, header_index: int) -> HeaderValuePair | None:
        for pair in self.pairs:
            if pair.header_row == header_row and pair.header_index == header_index:
                return pair
        return None


def _centres(boxes: Sequence[BoundingBox | None]) -> list[float | None]:
    return [None if box is None else box.x + box.width / 2 for box in boxes]


def _median(values: Sequence[float]) -> float:
    if not values:
        return 1.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _nearest(centre: float, candidates: Sequence[tuple[int, float]]) -> tuple[int, float] | None:
    if not candidates:
        return None
    index, value = min(candidates, key=lambda item: abs(item[1] - centre))
    return index, value


def detect_header_value_rows(
    rows: Sequence[tuple[str, Sequence[BoundingBox | None]]],
) -> HeaderValueModel:
    """Find header rows that are answered by the row directly beneath them."""
    pairs: list[HeaderValuePair] = []
    for index in range(len(rows) - 1):
        header_boxes = [box for box in rows[index][1] if box is not None]
        value_boxes = [box for box in rows[index + 1][1] if box is not None]
        if len(header_boxes) < MIN_HEADER_SEGMENTS or not value_boxes:
            continue

        widths = [box.width for box in header_boxes]
        median_width = _median(widths)
        if median_width <= 0:
            continue
        if max(widths) > MAX_HEADING_WIDTH_RATIO * median_width:
            continue

        header_centres = _centres(rows[index][1])
        value_centres = [
            (position, centre)
            for position, centre in enumerate(_centres(rows[index + 1][1]))
            if centre is not None
        ]
        tolerance = ALIGNMENT_TOLERANCE_RATIO * median_width

        for header_position, header_centre in enumerate(header_centres):
            if header_centre is None:
                continue
            nearest = _nearest(header_centre, value_centres)
            if nearest is None:
                continue
            value_position, value_centre = nearest
            error = abs(value_centre - header_centre)
            if error > tolerance:
                continue
            pairs.append(
                HeaderValuePair(
                    header_row=index,
                    value_row=index + 1,
                    header_index=header_position,
                    value_index=value_position,
                    alignment_error=round(error, 2),
                )
            )
    return HeaderValueModel(tuple(pairs))
