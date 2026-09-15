"""Deterministic OCR reading-order assembly.

OCR providers do not guarantee that detected text fields are returned in
natural reading order. When bounding boxes are
available we sort conservatively by vertical band then horizontal position;
when they are not, we preserve the provider's original order rather than
guessing a layout.
"""

from app.document_intelligence.ocr.models import OCRLine, OCRPage

_Y_BAND_PX = 12.0


def _sort_key(line: OCRLine) -> tuple[float, float]:
    box = line.bounding_box
    if box is None:
        return (0.0, 0.0)
    y_center = box.y + box.height / 2
    band = round(y_center / _Y_BAND_PX)
    return (band, box.x)


def order_lines(lines: list[OCRLine]) -> list[OCRLine]:
    if not lines or any(line.bounding_box is None for line in lines):
        return lines
    return sorted(lines, key=_sort_key)


def assemble_page_text(lines: list[OCRLine]) -> str:
    ordered = order_lines(lines)
    return "\n".join(line.text for line in ordered if line.text)


def assemble_document_text(pages: list[OCRPage]) -> str:
    """Join per-page text, preserving page boundaries with a blank line."""
    return "\n\n".join(page.text for page in pages if page.text)
