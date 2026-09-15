from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage
from app.document_intelligence.ocr.text_assembly import (
    assemble_document_text,
    assemble_page_text,
    order_lines,
)


def _line(text: str, x: float, y: float) -> OCRLine:
    return OCRLine(text=text, bounding_box=BoundingBox(x=x, y=y, width=10, height=10))


def test_orders_lines_by_reading_order_when_bounding_boxes_present() -> None:
    # Provider returns fields out of order; bounding boxes say line 1 is
    # above line 2, and within line 1, "world" is detected before "hello".
    lines = [
        _line("world", x=50, y=0),
        _line("line2", x=0, y=40),
        _line("hello", x=0, y=0),
    ]
    ordered = order_lines(lines)
    assert [line.text for line in ordered] == ["hello", "world", "line2"]


def test_assemble_page_text_joins_in_reading_order() -> None:
    lines = [_line("second", x=0, y=40), _line("first", x=0, y=0)]
    assert assemble_page_text(lines) == "first\nsecond"


def test_preserves_provider_order_without_bounding_boxes() -> None:
    lines = [OCRLine(text="b"), OCRLine(text="a")]
    assert order_lines(lines) == lines


def test_assemble_document_text_preserves_page_boundaries() -> None:
    pages = [
        OCRPage(page_number=1, text="page one"),
        OCRPage(page_number=2, text="page two"),
    ]
    assert assemble_document_text(pages) == "page one\n\npage two"


def test_assemble_document_text_skips_empty_pages() -> None:
    pages = [OCRPage(page_number=1, text=""), OCRPage(page_number=2, text="content")]
    assert assemble_document_text(pages) == "content"
