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
