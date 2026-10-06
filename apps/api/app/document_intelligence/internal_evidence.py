"""Facts a document says about itself, used to confirm OCR values from *inside* the document.

Everything here is computed from the OCR boxes of one document and is deliberately independent of
the box that holds the value it later confirms:

* **GPA arithmetic** -- the credit-weighted average of the semester GPAs (different boxes from the
  cumulative GPA), or total grade points / total credits where the page prints them.
* **Dates printed in several places** -- every box that holds a full date, with its position and
  whether the box is a *bare* date (nothing but the date, optionally "재학중").
* **Identifier shapes** -- corporate registration numbers printed on the page.

The module extracts facts only; deciding what they confirm is the policy's job
(`auto_acceptance.py`).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.document_intelligence.extraction.base import _source_observations
from app.document_intelligence.normalization.field_normalizer import (
    DATE_RE,
    canonicalize_numeric_text,
    normalize_date,
)
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage


@dataclass(frozen=True)
class DateBox:
    iso: str
    page: int
    x: float
    y: float
    width: float
    height: float
    bare: bool  # the box holds nothing but this date (optionally followed by "재학중")


@dataclass(frozen=True)
class GpaFacts:
    pairs: tuple[tuple[int, float], ...] = ()  # (credits, semester GPA), one per semester
    total_credits: int | None = None
    total_points: float | None = None
    semester_scales: tuple[str, ...] = ()
    legend_max: str | None = None  # the top grade value of the printed grading legend


@dataclass(frozen=True)
class DocFacts:
    dates: tuple[DateBox, ...] = ()
    gpa: GpaFacts | None = None
    corporate_numbers: tuple[str, ...] = ()
    entity_type: str | None = None  # "corporate" / "individual" when the form states it


_BARE_TAIL = re.compile(r"^\s*(재학\s*중)?\s*$")
_CREDITS = re.compile(r"(?<!총)취득학점\s*[:：]?\s*(\d{1,3})(?!\d)")
_TOTAL_CREDITS = re.compile(r"총\s*취득학점\s*[:：]?\s*(\d{1,4})(?!\d)")
_GPA = re.compile(r"평점평균\s*[:：]?\s*(\d\.\d{1,3})\s*/\s*(\d(?:\.\d{1,3})?)")
_LEGEND_MAX = re.compile(r"A\s*\+\s*=\s*(\d(?:\.\d{1,3})?)")
_CORP_NUMBER = re.compile(r"(?<!\d)(\d{6})\s*-\s*(\d{7})(?!\d)")
_NUMBER = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*$")


def _squash(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).split())


def _overlap_x(a: BoundingBox, b: BoundingBox) -> bool:
    return min(a.x + a.width, b.x + b.width) - max(a.x, b.x) > 0


def _lines(pages: list[dict]) -> OCRDocumentResult:
    ocr_pages = []
    for page in pages:
        lines = []
        for item in page.get("lines", []):
            box = item.get("bounding_box")
            lines.append(
                OCRLine(
                    text=item["text"],
                    confidence=item.get("confidence"),
                    bounding_box=BoundingBox(**box) if box else None,
                )
            )
        ocr_pages.append(
            OCRPage(
                page_number=page.get("page_number", 1),
                text="",
                lines=lines,
                metadata=page.get("metadata", {}),
            )
        )
    return OCRDocumentResult("facts", ocr_pages, "")


def extract_facts(pages: list[dict]) -> DocFacts:
    """`pages`: [{"page_number": n, "lines": [{"text", "bounding_box": {...}}...]}] (the stored OCR
    result rows)."""
    source = _lines(pages)
    segments: list[tuple[int, OCRLine]] = []
    for observation in _source_observations(source):
        for segment in observation.row.segments:
            if segment.text.strip() and segment.bounding_box is not None:
                segments.append((observation.row.page_number, segment))

    dates: list[DateBox] = []
    corporate: list[str] = []
    entity: str | None = None
    for page, segment in segments:
        folded = canonicalize_numeric_text(segment.text)
        box = segment.bounding_box
        assert box is not None
        matches = list(DATE_RE.finditer(folded))
        for match in matches:
            iso = normalize_date(match.group(0))
            if iso is None:
                continue
            tail = re.sub(
                r"^\s*일", "", folded[match.end() :]
            )  # the 일 of "20일" is part of the date
            remainder = folded[: match.start()] + tail
            dates.append(
                DateBox(
                    iso,
                    page,
                    box.x,
                    box.y,
                    box.width,
                    box.height,
                    len(matches) == 1 and bool(_BARE_TAIL.match(remainder)),
                )
            )
        corporate.extend(a + b for a, b in _CORP_NUMBER.findall(folded))
        squashed = _squash(segment.text)
        if "법인사업자" in squashed:
            entity = "corporate"
        elif "개인사업자" in squashed:
            entity = "individual"
    return DocFacts(tuple(dates), _gpa_facts(segments), tuple(corporate), entity)


def _gpa_facts(segments: list[tuple[int, OCRLine]]) -> GpaFacts | None:
    credits: list[tuple[int, BoundingBox, int]] = []
    totals: list[tuple[int, BoundingBox, int]] = []
    gpas: list[tuple[int, BoundingBox, float, str]] = []
    legend: str | None = None
    headers: dict[str, list[tuple[int, BoundingBox]]] = {"credits": [], "points": []}
    cells: list[tuple[int, BoundingBox, float]] = []
    for page, segment in segments:
        text = _squash(segment.text)
        box = segment.bounding_box
        assert box is not None
        if (m := _TOTAL_CREDITS.search(text)) is not None:
            totals.append((page, box, int(m.group(1))))
        elif (m := _CREDITS.search(text)) is not None:
            credits.append((page, box, int(m.group(1))))
        if (m := _GPA.search(text)) is not None:
            gpas.append((page, box, float(m.group(1)), m.group(2)))
        if (m := _LEGEND_MAX.search(text)) is not None:
            legend = m.group(1)
        if text == "총취득학점":
            headers["credits"].append((page, box))
        elif text == "총평점":
            headers["points"].append((page, box))
        elif (m := _NUMBER.match(segment.text)) is not None:
            cells.append((page, box, float(m.group(1))))
    if not gpas and not headers["credits"]:
        return None

    def below(anchor: tuple[int, BoundingBox]) -> float | None:
        page, box = anchor
        found = [
            (cell_box.y, value)
            for cell_page, cell_box, value in cells
            if cell_page == page
            and 0 <= cell_box.y - (box.y + box.height) <= 3 * box.height
            and _overlap_x(box, cell_box)
        ]
        return min(found)[1] if found else None

    total_credits = None
    total_points = None
    if headers["credits"]:
        value = below(headers["credits"][0])
        total_credits = int(value) if value is not None else None
    if headers["points"]:
        total_points = below(headers["points"][0])
    if total_credits is None and totals:
        total_credits = totals[0][2]

    pairs: list[tuple[int, float]] = []
    for page, box, gpa, _scale in gpas:
        # the cumulative GPA is the one printed right under the "총 취득학점" line
        if any(
            t_page == page
            and 0 < box.y - t_box.y <= 3 * max(box.height, t_box.height)
            and _overlap_x(box, t_box)
            for t_page, t_box, _ in totals
        ):
            continue
        above = [
            (box.y - c_box.y, c_value)
            for c_page, c_box, c_value in credits
            if c_page == page and 0 < box.y - c_box.y <= 6 * box.height and _overlap_x(box, c_box)
        ]
        if above:
            pairs.append((min(above)[1], gpa))
    return GpaFacts(
        pairs=tuple(pairs),
        total_credits=total_credits,
        total_points=total_points,
        semester_scales=tuple(scale for _, _, _, scale in gpas),
        legend_max=legend,
    )


def corporate_number_valid(number: str) -> bool:
    """Check digit of a 13-digit 법인등록번호 (commonly published algorithm: weights 1,2,1,2,...
    on the first twelve digits; check = (10 - sum mod 10) mod 10). Format validation only --
    it passes by chance one time in ten and never confirms anything on its own."""
    digits = re.sub(r"\D", "", number)
    if len(digits) != 13:
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 2) for i, d in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == int(digits[12])
