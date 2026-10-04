"""Tests for the P1 structural layout layer.

These test the *derived structure* in isolation: what geometry the layer
reports, and what it refuses to report. They deliberately do not assert any
field value, because measurement showed that no field outcome on the frozen
corpus changes when this layer is enabled. Asserting a field value here would
be asserting a lucky answer.
"""

from __future__ import annotations

import math

import pytest

from app.document_intelligence.layout import (
    build_page_structure,
    detect_header_value_rows,
    infer_columns,
    infer_sections,
)
from app.document_intelligence.layout.columns import COLUMN_GAP_RATIO, Column
from app.document_intelligence.ocr.layout import TextRow, build_rows
from app.document_intelligence.ocr.models import BoundingBox, OCRLine

# ---------------------------------------------------------------- helpers


def line(text: str, x: float, y: float, width: float, height: float = 30.0) -> OCRLine:
    return OCRLine(
        text=text,
        confidence=0.95,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
    )


def row(page: int, segments: list[OCRLine]) -> TextRow:
    return TextRow(page_number=page, segments=tuple(segments))


def boxes(rows: list[TextRow]) -> list[BoundingBox]:
    return [
        segment.bounding_box
        for item in rows
        for segment in item.segments
        if segment.bounding_box is not None
    ]


# ---------------------------------------------------------------- columns


def test_single_column_form_is_not_split_into_columns() -> None:
    """A key/value certificate has one wide label column and must stay one column."""
    # A narrow label/value gap must not be read as a table column.
    narrow = [
        row(1, [line("성    명:", 40, 100, 180), line("홍길동", 240, 100, 160)]),
        row(1, [line("학    번:", 40, 160, 180), line("12345678", 240, 160, 160)]),
    ]
    assert infer_columns(boxes(narrow)).is_single_column()

    # A wide gap does yield exactly two bands (label | value). That is correct
    # and harmless: columns constrain candidate association, they never gate the
    # same-row path that already resolves this form.
    wide = [
        row(1, [line("성    명:", 40, 100, 180), line("홍길동", 300, 100, 160)]),
        row(1, [line("학    번:", 40, 160, 180), line("12345678", 300, 160, 160)]),
    ]
    model = infer_columns(boxes(wide))

    assert len(model.columns) == 2
    assert model.column_for(BoundingBox(40, 100, 180, 30)) is model.columns[0]
    assert model.column_for(BoundingBox(300, 100, 160, 30)) is model.columns[1]


def test_wide_gap_between_same_baseline_boxes_becomes_a_column_boundary() -> None:
    """The measured transcript failure: two table cells on one baseline."""
    rows = [
        row(
            1,
            [
                line("평점평균:3.50/4.0", 40, 100, 320),
                line("백분율:85.00/100", 700, 100, 300),
            ],
        )
    ]
    model = infer_columns(boxes(rows))

    assert len(model.columns) >= 2
    first, second = model.columns[0], model.columns[1]
    assert first.contains(BoundingBox(40, 100, 320, 30))
    assert second.contains(BoundingBox(700, 100, 300, 30))


def test_letter_spaced_label_is_not_mistaken_for_a_column() -> None:
    """Intra-word spacing must not create a column boundary."""
    rows = [
        row(1, [line("경", 40, 100, 30), line("북", 90, 100, 30), line("대학교", 140, 100, 120)])
    ]
    model = infer_columns(boxes(rows))

    assert model.is_single_column()


def test_column_clip_reports_none_for_a_box_outside_the_band() -> None:
    column = Column(0, 100.0, 200.0)

    assert column.clip(BoundingBox(120, 0, 40, 20)) == (120.0, 160.0)
    assert column.clip(BoundingBox(400, 0, 40, 20)) is None


def test_column_detection_is_insensitive_to_ordinary_spacing() -> None:
    """Counterexample guard: the threshold must not sit on a knife edge.

    Two layouts that differ only in label spacing must both be read as a single
    column. If a future change to COLUMN_GAP_RATIO breaks this, the constant has
    become a fitted number rather than a structural one.
    """
    for spacing in (0.0, 2.0, 5.0, 9.0):
        rows = [row(1, [line("성", 40, 100, 30), line("명:", 40 + 30 + spacing, 100, 60)])]
        assert infer_columns(boxes(rows)).is_single_column(), spacing


# ---------------------------------------------------------------- sections


def test_uniform_spacing_produces_one_section() -> None:
    rows = [row(1, [line(f"line{i}", 40, 100 + i * 40, 200, 30)]) for i in range(6)]
    model = infer_sections([(item.text, [s.bounding_box for s in item.segments]) for item in rows])

    assert len(model.sections) == 1
    assert model.section_for(3) is not None
    assert model.section_index_for(3) == 0


def test_large_vertical_gap_starts_a_new_section() -> None:
    rows = [
        row(1, [line("a", 40, 100, 100, 30)]),
        row(1, [line("b", 40, 140, 100, 30)]),
        row(1, [line("c", 40, 180, 100, 30)]),
        row(1, [line("d", 40, 600, 100, 30)]),
        row(1, [line("e", 40, 640, 100, 30)]),
        row(1, [line("f", 40, 680, 100, 30)]),
    ]
    model = infer_sections([(item.text, [s.bounding_box for s in item.segments]) for item in rows])

    assert len(model.sections) >= 2
    assert model.repeated_across_sections([0, 4])


def test_bracketed_heading_opens_a_section_and_is_recorded() -> None:
    rows = [
        row(1, [line("<<2024학년도 1학기>>", 40, 100, 300, 30)]),
        row(1, [line("평점평균:3.29/4.0", 40, 140, 300, 30)]),
        row(1, [line("<<2024학년도 2학기>>", 40, 600, 300, 30)]),
        row(1, [line("평점평균:3.62/4.0", 40, 640, 300, 30)]),
    ]
    model = infer_sections([(item.text, [s.bounding_box for s in item.segments]) for item in rows])

    headings = [section.heading for section in model.sections if section.heading]
    assert any("2024학년도 1학기" in (heading or "") for heading in headings)
    assert model.repeated_across_sections([1, 3])


def test_parenthetical_subcaption_is_not_treated_as_a_section_heading() -> None:
    """Adversarial: '(법인사업자)' is a qualifier, not a block heading.

    Treating it as a heading split one business certificate into three phantom
    sections. Only double-angle and square brackets qualify.
    """
    rows = [
        row(1, [line("(법인사업자)", 40, 100, 200, 30)]),
        row(1, [line("등록번호:368-88-03013", 40, 140, 400, 30)]),
        row(1, [line("법인 영(단체영): (주)예시상사", 40, 180, 600, 30)]),
        row(1, [line("자:이상옥", 40, 220, 200, 30)]),
        row(1, [line("개업연월일:2024년06월24일", 40, 260, 400, 30)]),
    ]
    model = infer_sections([(item.text, [s.bounding_box for s in item.segments]) for item in rows])

    assert len(model.sections) == 1


def test_repeated_rows_in_one_section_are_not_reported_as_cross_section() -> None:
    rows = [
        row(1, [line("전공:글로벌소프트웨어융합전공", 40, 100 + i * 40, 600, 30)]) for i in range(4)
    ]
    model = infer_sections([(item.text, [s.bounding_box for s in item.segments]) for item in rows])

    assert not model.repeated_across_sections([0, 3])


# ---------------------------------------------------------------- headers


def test_summary_header_row_pairs_with_the_value_row_beneath_it() -> None:
    """The measured P1-003 structure: heading row, value row, aligned columns."""
    rows = [
        row(
            1,
            [
                line("총취득학점", 60, 100, 160),
                line("총 평 점", 300, 100, 160),
                line("총평점평균", 540, 100, 160),
            ],
        ),
        row(
            1,
            [
                line("175.0", 60, 140, 160),
                line("710.75", 300, 140, 160),
                line("3.90/4.0", 540, 140, 160),
            ],
        ),
    ]
    model = detect_header_value_rows(
        [(item.text, [s.bounding_box for s in item.segments]) for item in rows]
    )
    pair = model.value_for(0, 2)

    assert pair is not None
    assert pair.value_row == 1
    assert pair.value_index == 2
    assert rows[1].segments[pair.value_index].text == "3.90/4.0"


def test_misaligned_value_row_produces_no_pairing() -> None:
    """Adversarial: alignment must be required, not assumed."""
    rows = [
        row(1, [line("heading one", 60, 100, 160), line("heading two", 300, 100, 160)]),
        row(1, [line("value one", 900, 140, 160), line("value two", 1100, 140, 160)]),
    ]
    model = detect_header_value_rows(
        [(item.text, [s.bounding_box for s in item.segments]) for item in rows]
    )

    assert model.pairs == ()


def test_two_segment_row_is_left_to_the_cheaper_same_row_path() -> None:
    """Below the header-segment floor, so header/value logic stays out of the way."""
    rows = [
        row(1, [line("label one", 60, 100, 160), line("label two", 300, 100, 160)]),
        row(1, [line("value one", 60, 140, 160), line("value two", 300, 140, 160)]),
    ]
    model = detect_header_value_rows(
        [(item.text, [s.bounding_box for s in item.segments]) for item in rows]
    )

    assert model.pairs == ()


def test_wide_heading_segment_is_treated_as_a_value_not_a_heading() -> None:
    rows = [
        row(
            1,
            [
                line("짧은제목", 60, 100, 100),
                line("아주 긴 값이 들어 있는 박스", 200, 100, 900),
                line("셋째", 1200, 100, 100),
            ],
        ),
        row(
            1, [line("1.0", 60, 140, 100), line("2.0", 200, 140, 900), line("3.0", 1200, 140, 100)]
        ),
    ]
    model = detect_header_value_rows(
        [(item.text, [s.bounding_box for s in item.segments]) for item in rows]
    )

    assert model.pairs == ()


# ---------------------------------------------------------------- integration


def test_structure_is_page_scoped() -> None:
    rows = [row(1, [line("page one", 40, 100, 200, 30)])]
    structure = build_page_structure(rows)

    assert structure.page_number == 1
    assert not structure.has_multi_column_layout()


def test_build_rows_and_structure_agree_on_a_label_value_form() -> None:
    """The layout layer must not disturb a form that already worked."""
    page_lines = [
        line("성    명:", 40, 100, 180),
        line("홍길동", 300, 100, 160),
        line("학    번:", 40, 160, 180),
        line("12345678", 300, 160, 160),
    ]
    from app.document_intelligence.ocr.models import OCRPage

    rows = build_rows(OCRPage(page_number=1, text="", lines=page_lines))
    structure = build_page_structure(rows)

    assert len(rows) == 2
    assert len(structure.columns.columns) <= 2
    assert not structure.has_header_value_rows()


def test_empty_page_produces_empty_models() -> None:
    assert infer_columns([]).columns == ()
    assert infer_sections([]).sections == ()
    assert detect_header_value_rows([]).pairs == ()


@pytest.mark.parametrize("gap_ratio", [COLUMN_GAP_RATIO])
def test_column_gap_ratio_is_positive(gap_ratio: float) -> None:
    assert gap_ratio > 0
    assert math.isfinite(gap_ratio)
