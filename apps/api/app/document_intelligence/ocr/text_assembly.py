"""Deterministic OCR reading-order assembly.

OCR providers do not guarantee that detected text fields are returned in
natural reading order. When bounding boxes are
available we sort conservatively by vertical band then horizontal position;
when they are not, we preserve the provider's original order rather than
guessing a layout.
"""

import re
import statistics
from dataclasses import replace

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


_CONTENT_CHAR_RE = re.compile(r"[가-힣A-Za-z0-9]")
_EDGE_MARKS = "'\u2018\u2019`\""
_NOISE_MAX_CHARS = 2
_NOISE_MAX_CONFIDENCE = 0.5
_NOISE_MAX_HEIGHT_RATIO = 0.5


def drop_noise_boxes(lines: list[OCRLine]) -> list[OCRLine]:
    """Remove the stray marks a recogniser adds around large, letter-spaced print.

    A title read one glyph per box ("재 학 증 명 서") picks up boxes such as "−" (conf 0.37) or
    "그" (conf 0.12, a few pixels wide) between its glyphs, and quote marks glued to a glyph
    ("'증"). The classifier squashes whitespace but cannot skip those characters, so the title no
    longer matches. A box is dropped only when it holds no letter or digit at all, or when it is at
    most two characters, below 0.5 confidence AND under half the median box height. Quote marks at
    a box's edges are trimmed. Lines without geometry are returned untouched."""
    boxed = [line for line in lines if line.bounding_box is not None]
    if not boxed:
        return lines
    median_height = statistics.median(line.bounding_box.height for line in boxed)  # type: ignore[union-attr]
    kept: list[OCRLine] = []
    for line in lines:
        text = line.text.strip(_EDGE_MARKS + " ")
        box = line.bounding_box
        if box is None:
            kept.append(line)
            continue
        if not _CONTENT_CHAR_RE.search(text):
            continue
        if (
            len(text.replace(" ", "")) <= _NOISE_MAX_CHARS
            and line.confidence is not None
            and line.confidence < _NOISE_MAX_CONFIDENCE
            and box.height < _NOISE_MAX_HEIGHT_RATIO * median_height
        ):
            continue
        kept.append(replace(line, text=text) if text != line.text else line)
    return kept


def denoised_pages(pages: list[OCRPage]) -> list[OCRPage]:
    """Pages for classification and the title gate. Embedded PDF text is exact and passes through."""
    out: list[OCRPage] = []
    for page in pages:
        if page.metadata.get("source") == "direct_pdf_text" or not page.lines:
            out.append(page)
            continue
        lines = drop_noise_boxes(page.lines)
        out.append(replace(page, lines=lines, text=assemble_page_text(lines)))
    return out
