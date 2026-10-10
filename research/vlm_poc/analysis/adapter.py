"""Turns PaddleOCR-VL page blocks into the OCR page shape the production extractors read.

Research code: it imports the app's dataclasses (read-only), never the other way round.
Each text line of a block becomes one OCRLine inside the block box (the VLM gives no per-line
geometry and no confidence). Tables become one line per row, cells joined by two spaces.
"""
import html
import os
import re

from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_MODE = os.environ.get("ADAPTER_MODE", "both")  # "rows" = one line per table row (first variant)


def _text_lines(label: str, content: str) -> list[str]:
    if not content:
        return []
    if "<table" in content.lower() or label == "table":
        rows = []
        for row in _ROW.findall(content):
            cells = [html.unescape(_TAG.sub("", c)).strip() for c in _CELL.findall(row)]
            cells = [c.replace("\\n", " ").replace("\n", " ") for c in cells if c]
            if not cells:
                continue
            if _MODE in ("pairs", "adjacent", "both") and len(cells) % 2 == 0 and len(cells) >= 2:
                # label, value, label, value ... -> "label : value" lines (the extractors read an explicit colon)
                rows.extend(f"{cells[i]} : {cells[i + 1]}" for i in range(0, len(cells), 2))
            elif _MODE == "adjacent" and len(cells) >= 2:
                # also offer every short cell as a label for the cell after it (rowspans break the even pairing)
                rows.append("  ".join(cells))
                rows.extend(f"{cells[i]} : {cells[i + 1]}" for i in range(len(cells) - 1) if len(cells[i]) <= 14)
            else:
                rows.append("  ".join(cells))
        return rows
    lines = []
    for raw in content.replace("\r", "").split("\n"):
        line = re.sub(r"^#+\s*", "", html.unescape(_TAG.sub("", raw))).strip()
        if line:
            lines.append(line)
    return lines


_TD = re.compile(r"<t([dh])([^>]*)>(.*?)</t[dh]>", re.S | re.I)


def _grid_cells(content: str) -> list[tuple[str, int, int, int, int]]:
    """(text, row, col, rowspan, colspan) for every non-empty cell, honouring row/col spans."""
    cells: list[tuple[str, int, int, int, int]] = []
    occupied: set[tuple[int, int]] = set()
    for r, row in enumerate(_ROW.findall(content)):
        c = 0
        for _kind, attrs, inner in _TD.findall(row):
            while (r, c) in occupied:
                c += 1
            cs = int((re.search(r'colspan="(\d+)"', attrs) or [0, 1])[1])
            rs = int((re.search(r'rowspan="(\d+)"', attrs) or [0, 1])[1])
            for dr in range(rs):
                for dc in range(cs):
                    occupied.add((r + dr, c + dc))
            text = re.sub(r"\s+", " ", html.unescape(_TAG.sub("", inner).replace("\\n", " "))).strip()
            if text:
                cells.append((text, r, c, rs, cs))
            c += cs
    return cells


def _grid_lines(content: str, bbox: list[float]) -> list[OCRLine]:
    cells = _grid_cells(content)
    if not cells:
        return []
    rows = max(r + rs for _t, r, _c, rs, _cs in cells)
    cols = max(c + cs for _t, _r, c, _rs, cs in cells)
    x0, y0, x1, y1 = (float(v) for v in bbox)
    cw, rh = max(x1 - x0, 1.0) / cols, max(y1 - y0, 1.0) / rows
    return [
        OCRLine(text=t, confidence=None, bounding_box=BoundingBox(x=x0 + c * cw, y=y0 + r * rh, width=cs * cw, height=rs * rh))
        for t, r, c, rs, cs in cells
    ]


def page_from_blocks(page: dict) -> OCRPage:
    lines: list[OCRLine] = []
    for block in page.get("blocks", []):
        if _MODE == "both" and ("<table" in (block.get("block_content") or "").lower()) and block.get("block_bbox"):
            lines.extend(_grid_lines(block["block_content"], block["block_bbox"]))
            # plus the "label : value" row lines inside the block box (first variant that worked)
            texts = _text_lines("table", block["block_content"].replace("<td", "<td"))
            bbox = [float(v) for v in block["block_bbox"]]
            global _MODE_PAIRS
            height = max(bbox[3] - bbox[1], 1.0) / max(len(texts), 1)
            for index, text in enumerate(texts):
                lines.append(OCRLine(text=text, confidence=None, bounding_box=BoundingBox(x=bbox[0], y=bbox[1] + index * height, width=bbox[2] - bbox[0], height=height)))
            continue
        if _MODE == "grid" and ("<table" in (block.get("block_content") or "").lower()) and block.get("block_bbox"):
            lines.extend(_grid_lines(block["block_content"], block["block_bbox"]))
            continue
        texts = _text_lines(block.get("block_label") or "", block.get("block_content") or "")
        bbox = block.get("block_bbox")
        if not texts or not bbox:
            continue
        x0, y0, x1, y1 = (float(v) for v in bbox)
        height = max(y1 - y0, 1.0) / len(texts)
        for index, text in enumerate(texts):
            lines.append(
                OCRLine(text=text, confidence=None, bounding_box=BoundingBox(x=x0, y=y0 + index * height, width=max(x1 - x0, 1.0), height=height))
            )
    # keep the model's reading order (top to bottom, then left to right) as the extractors expect
    lines.sort(key=lambda line: (round(line.bounding_box.y / 8), line.bounding_box.x))
    text = "\n".join(line.text for line in lines)
    return OCRPage(
        page_number=int(page["page_number"]),
        text=text,
        lines=lines,
        confidence=None,
        metadata={"provider": "paddleocr-vl-1.6", "source": "ocr", "coordinate_space": "pixel",
                  "width": page.get("width"), "height": page.get("height")},
    )
