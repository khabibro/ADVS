"""A low-confidence box read from a seal must not chain neighbouring rows into one; its text is kept. Invented data."""

from app.document_intelligence.ocr.layout import build_rows
from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage


def line(text: str, x: float, y: float, h: float, conf: float | None = 0.95, **kw) -> OCRLine:
    return OCRLine(
        text=text, confidence=conf, bounding_box=BoundingBox(x, y, 8 * len(text), h), **kw
    )


def rows_of(lines: list[OCRLine]) -> list[str]:
    return [row.text for row in build_rows(OCRPage(1, "", lines))]


def page(seal_conf: float | None, **kw) -> list[OCRLine]:
    return [
        line("위의 사실을 증명합니다.", 100, 100, 24),
        line("2031년 05월 03일", 120, 128, 27),
        line("가나다 대학교", 60, 160, 40),
        line("㉠㉡", 300, 110, 77, seal_conf, **kw),  # a tall seal box overlapping all three rows
    ]


def test_an_unflagged_tall_box_still_chains_rows() -> None:
    assert len(rows_of(page(0.26))) < 3  # no flag, no isolation: behaviour unchanged


def test_flagged_seal_box_does_not_chain_rows_and_its_text_is_kept() -> None:
    rows = rows_of(page(0.26, bridge_exempt=True))
    assert "2031년 05월 03일" in rows  # the date is a row of its own again
    assert any("㉠㉡" in row for row in rows)  # nothing was dropped
    assert len(rows) == 4


def test_stacked_labels_are_split_when_the_colon_is_detected_with_the_value() -> None:
    from app.document_intelligence.ocr.layout import split_stacked_label_boxes

    lines = [
        line(
            "학성", 100, 100, 44
        ),  # first syllables of two stacked labels, fused into one tall box
        line("번", 160, 102, 18),  # the label tail, without its colon
        line(":1234567890", 178, 100, 22),  # the colon starts the value box
        line("명", 160, 122, 18),
        line(":김하늘", 178, 122, 22),
    ]
    texts = sorted(item.text for item in split_stacked_label_boxes(lines) if item.text in "학성")
    assert texts == ["성", "학"]


def test_a_fused_box_without_tails_on_every_row_is_left_alone() -> None:
    from app.document_intelligence.ocr.layout import split_stacked_label_boxes

    lines = [
        line("학성", 100, 100, 44),
        line("번", 160, 102, 18),
        line(":1234567890", 178, 100, 22),
    ]
    assert [
        item.text for item in split_stacked_label_boxes(lines) if item.text in ("학성", "학", "성")
    ] == ["학성"]
