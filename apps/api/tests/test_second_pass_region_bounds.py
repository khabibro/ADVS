"""The second-pass crop around a value does not take in the rows above and below it (invented boxes)."""

from app.document_intelligence.ocr.models import BoundingBox
from app.document_intelligence.ocr.providers import region_bounds

W, H = 1000, 1400
VALUE = BoundingBox(x=300, y=1000, width=400, height=40)
DATE_ROW_ABOVE = BoundingBox(x=250, y=950, width=500, height=48)  # ends at y=998, nearly touching the value
FOOTER_BELOW = BoundingBox(x=250, y=1045, width=500, height=30)


def test_without_neighbours_the_crop_is_the_value_plus_margin() -> None:
    assert region_bounds(VALUE, (), W, H) == (284, 988, 716, 1052)


def test_a_row_above_cuts_the_top() -> None:
    left, top, right, bottom = region_bounds(VALUE, (DATE_ROW_ABOVE,), W, H)
    assert top == 998 and (left, right, bottom) == (284, 716, 1052)


def test_a_row_below_cuts_the_bottom() -> None:
    assert region_bounds(VALUE, (FOOTER_BELOW,), W, H)[3] == 1045


def test_a_neighbour_beside_the_crop_is_ignored() -> None:
    beside = BoundingBox(x=800, y=950, width=100, height=48)
    assert region_bounds(VALUE, (beside,), W, H) == region_bounds(VALUE, (), W, H)


def test_a_neighbour_overlapping_the_value_never_cuts_into_it() -> None:
    overlapping = BoundingBox(x=250, y=960, width=500, height=70)  # reaches y=1030, into the value
    _, top, _, bottom = region_bounds(VALUE, (overlapping,), W, H)
    assert top == 1000 and bottom == 1052  # the margin above is gone, the value box is whole


def test_the_crop_stays_inside_the_page() -> None:
    corner = BoundingBox(x=2, y=2, width=100, height=20)
    left, top, right, bottom = region_bounds(corner, (), W, H)
    assert (left, top) == (0, 0) and right <= W and bottom <= H
