"""One call site that derives every structural view for a page.

Structural views are pure functions of the row model, so they are computed
once per page and shared. ``PageStructure`` deliberately holds no field
knowledge: it says what shape the page has, not what any field means.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.document_intelligence.layout.columns import ColumnModel, infer_columns
from app.document_intelligence.layout.headers import HeaderValueModel, detect_header_value_rows
from app.document_intelligence.layout.sections import SectionModel, infer_sections
from app.document_intelligence.ocr.layout import TextRow
from app.document_intelligence.ocr.models import BoundingBox


@dataclass(frozen=True)
class PageStructure:
    """Structural views of one page's rows."""

    page_number: int
    columns: ColumnModel
    sections: SectionModel
    headers: HeaderValueModel

    def has_multi_column_layout(self) -> bool:
        return not self.columns.is_single_column()

    def has_sections(self) -> bool:
        return len(self.sections.sections) > 1

    def has_header_value_rows(self) -> bool:
        return bool(self.headers.pairs)


def _rows_payload(rows: Sequence[TextRow]) -> list[tuple[str, Sequence[BoundingBox | None]]]:
    return [(row.text, [segment.bounding_box for segment in row.segments]) for row in rows]


def build_page_structure(rows: Sequence[TextRow]) -> PageStructure:
    """Derive columns, sections and header/value pairings for one page."""
    payload = _rows_payload(rows)
    boxes = [box for _text, segment_boxes in payload for box in segment_boxes if box is not None]
    return PageStructure(
        page_number=rows[0].page_number if rows else 1,
        columns=infer_columns(boxes),
        sections=infer_sections(payload),
        headers=detect_header_value_rows(payload),
    )


def build_document_structures(pages: Sequence[Sequence[TextRow]]) -> dict[int, PageStructure]:
    """One structure per page, keyed by page number.

    Pages are scoped independently: no structure is ever built across pages,
    which is what keeps a label on one page from binding to a value on another.
    """
    return {rows[0].page_number: build_page_structure(rows) for rows in pages if rows}
