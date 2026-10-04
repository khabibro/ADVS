"""Column inference from OCR geometry.

The existing row model is deliberately one-dimensional: boxes join a row when
their vertical spans overlap, and a row is then ordered left to right. That is
correct for a label/value form, and wrong for a ruled table, where several
independent cells share a baseline. On a real transcript the grade-point cell
and the percentage cell sit roughly 770 px apart on the same baseline, so both
end up inside one row and the text extracted after a label carries its
neighbour's content.

This module recovers the vertical bands that the row model flattened. It uses
only box geometry and two named constants; it has no knowledge of document
type, field name or language.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.document_intelligence.ocr.models import BoundingBox

# A gap between horizontally adjacent boxes counts as a column boundary when
# it is at least this multiple of the taller neighbour's line height. One
# character of ordinary letter spacing is far below it; an empty table cell
# is far above it. Centralised here so a counterexample can be tested against
# one number rather than a threshold buried in a scoring function.
COLUMN_GAP_RATIO = 1.2

# A column must be at least this fraction of the page's occupied width. This
# stops a stray wide gap near a margin from being promoted to a column.
MIN_COLUMN_WIDTH_RATIO = 0.04


@dataclass(frozen=True)
class Column:
    """One vertical band of the page, in source units."""

    index: int
    left: float
    right: float

    def contains(self, box: BoundingBox) -> bool:
        """True when `box` sits inside this band, allowing small overhangs."""
        centre = box.x + box.width / 2
        return self.left <= centre <= self.right

    def clip(self, box: BoundingBox) -> tuple[float, float] | None:
        """Horizontal extent of `box` restricted to this column.

        Returns None when the box does not reach into the band at all.
        """
        left = max(box.x, self.left)
        right = min(box.x + box.width, self.right)
        if right <= left:
            return None
        return left, right


@dataclass(frozen=True)
class ColumnModel:
    """Column bands for one page, plus the page extent they were derived from."""

    columns: tuple[Column, ...]
    page_left: float
    page_right: float

    @property
    def page_width(self) -> float:
        return self.page_right - self.page_left

    def column_for(self, box: BoundingBox) -> Column | None:
        """The column whose band contains `box`, by centre point.

        Boxes that straddle two bands are attributed to the band holding their
        centre, which keeps a wide merged cell attached to one column instead
        of being dropped.
        """
        for column in self.columns:
            if column.contains(box):
                return column
        return None

    def is_single_column(self) -> bool:
        return len(self.columns) <= 1


def _line_height(box: BoundingBox) -> float:
    return max(box.height, 1.0)


def collect_boundary_gaps(boxes: Sequence[BoundingBox]) -> list[tuple[float, float]]:
    """Gaps between horizontally adjacent boxes that read as column boundaries.

    Returns (gap_width, reference_line_height) pairs. Boxes are grouped into
    visual baselines first, because two boxes on different rows are not
    horizontally adjacent at all.
    """
    grouped: dict[int, list[BoundingBox]] = {}
    for box in boxes:
        grouped.setdefault(_baseline_key(box), []).append(box)

    gaps: list[tuple[float, float]] = []
    for row in grouped.values():
        ordered = sorted(row, key=lambda item: item.x)
        for left, right in zip(ordered, ordered[1:], strict=False):
            gap = right.x - (left.x + left.width)
            reference = max(_line_height(left), _line_height(right))
            if gap >= COLUMN_GAP_RATIO * reference:
                gaps.append((gap, reference))
    return gaps


def _baseline_key(box: BoundingBox, tolerance_ratio: float = 0.5) -> int:
    """Bucket a box into a visual baseline.

    Uses the same overlap notion the row model uses, so the two agree on what
    "the same line" means.
    """
    centre = box.y + box.height / 2
    return int(centre // max(_line_height(box) * tolerance_ratio, 1.0))


def infer_columns(boxes: Iterable[BoundingBox]) -> ColumnModel:
    """Infer page column bands from the geometry of `boxes`.

    A page with no qualifying gap is a single column, which is the common case
    for a key/value certificate and must stay a single column so that nothing
    downstream is perturbed for documents that were already fine.
    """
    materialised = [box for box in boxes if box is not None]
    if not materialised:
        return ColumnModel((), 0.0, 0.0)

    left = min(box.x for box in materialised)
    right = max(box.x + box.width for box in materialised)
    width = right - left
    if width <= 0:
        return ColumnModel((Column(0, left, right),), left, right)

    boundaries = collect_boundary_gaps(materialised)
    min_gap = MIN_COLUMN_WIDTH_RATIO * width

    # A boundary is a cut position midway across the gap it came from. Every
    # qualifying gap contributes, so a three- or four-column table yields all
    # of its column edges rather than only its widest.
    cuts: list[float] = []
    for gap, _reference in boundaries:
        for midpoint in _cut_positions(gap, materialised):
            if left < midpoint < right:
                cuts.append(midpoint)
    cuts = sorted(set(round(cut, 2) for cut in cuts))

    # Merge cuts that would produce a column narrower than the minimum.
    kept: list[float] = []
    for cut in cuts:
        if not kept or cut - kept[-1] >= min_gap:
            kept.append(cut)

    edges = [left, *kept, right]
    columns = tuple(
        Column(index, edges[index], edges[index + 1]) for index in range(len(edges) - 1)
    )
    return ColumnModel(columns, left, right)


def _cut_positions(gap: float, boxes: Sequence[BoundingBox]) -> list[float]:
    """Midpoints of every baseline gap at least as wide as `gap`.

    Using the widest gap as the yardstick, rather than the per-gap
    reference height, keeps one noisy tall box from introducing a cut that
    the rest of the page does not support.
    """
    grouped: dict[int, list[BoundingBox]] = {}
    for box in boxes:
        grouped.setdefault(_baseline_key(box), []).append(box)
    positions: list[float] = []
    for row in grouped.values():
        ordered = sorted(row, key=lambda item: item.x)
        for left_box, right_box in zip(ordered, ordered[1:], strict=False):
            spacing = right_box.x - (left_box.x + left_box.width)
            reference = max(_line_height(left_box), _line_height(right_box))
            if spacing >= max(gap, COLUMN_GAP_RATIO * reference):
                positions.append(left_box.x + left_box.width + spacing / 2)
    return positions
