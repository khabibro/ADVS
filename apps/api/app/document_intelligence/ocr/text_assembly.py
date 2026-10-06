"""Deterministic OCR reading-order assembly.

OCR providers do not guarantee that detected text fields are returned in
natural reading order. When bounding boxes are
available we sort conservatively by vertical band then horizontal position;
when they are not, we preserve the provider's original order rather than
guessing a layout.
"""

from app.document_intelligence.ocr.models import OCRLine, OCRPage

_OVERLAP_RATIO = 0.5


def order_lines(lines: list[OCRLine]) -> list[OCRLine]:
    """Reading order = visual rows top to bottom, left to right inside a row.

    Rows are decided by vertical *overlap*, not by fixed-height bands: a letter-spaced
    title ("성 적 증 명 서") is detected as one box per character, and a few pixels of
    baseline jitter used to push boxes of the same title into different bands and scramble
    the title ("1적 증 명 서 성"), so its classification signal was lost.
    """
    if not lines or any(line.bounding_box is None for line in lines):
        return lines
    by_center = sorted(
        lines,
        key=lambda line: (
            line.bounding_box.y + line.bounding_box.height / 2,  # type: ignore[union-attr]
            line.bounding_box.x,  # type: ignore[union-attr]
        ),
    )
    rows: list[list[OCRLine]] = [[by_center[0]]]
    for line in by_center[1:]:
        anchor = rows[-1][-1]
        if _vertical_overlap(anchor, line) >= _OVERLAP_RATIO * min(
            anchor.bounding_box.height,  # type: ignore[union-attr]
            line.bounding_box.height,  # type: ignore[union-attr]
        ):
            rows[-1].append(line)
        else:
            rows.append([line])
    return [
        line
        for row in rows
        for line in sorted(row, key=lambda item: item.bounding_box.x)  # type: ignore[union-attr]
    ]


def _vertical_overlap(left: OCRLine, right: OCRLine) -> float:
    a, b = left.bounding_box, right.bounding_box
    assert a is not None and b is not None
    return min(a.y + a.height, b.y + b.height) - max(a.y, b.y)


def assemble_page_text(lines: list[OCRLine]) -> str:
    ordered = order_lines(lines)
    return "\n".join(line.text for line in ordered if line.text)


def assemble_document_text(pages: list[OCRPage]) -> str:
    """Join per-page text, preserving page boundaries with a blank line."""
    return "\n\n".join(page.text for page in pages if page.text)
