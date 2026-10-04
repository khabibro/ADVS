"""Structural layout derived from OCR geometry.

P1 rationale
------------
OCR answers "what text is visible". This package answers "how is that text
organised", using only geometry that already exists in
:class:`~app.document_intelligence.ocr.models.OCRLine`. It adds no new OCR
dependency, no new model, and no second pass over the pixels.

Three structures are derived, each because a measured failure on real scanned
Korean administrative documents demanded it:

``columns``
    The pre-existing row model groups by vertical overlap and is therefore
    one-dimensional: any boxes sharing a baseline become a single row,
    however far apart they are horizontally. On a ruled table this merges
    the "grade point average" cell with the "percentage" cell that sits
    770 px to its right, so the extracted value for a label arrives
    contaminated with its neighbour. Column inference recovers the vertical
    bands that the row model flattened.

``sections``
    A repeated label in a long document usually means "the same field once
    per block", not "the same field with seven candidate values". A page is
    partitioned into sections from large vertical gaps and from explicit
    bracketed headings, so a repeated label can be scoped to the block that
    owns it instead of being pooled into one ambiguous set.

``headers``
    Summary tables print a header row and its values in the next row, with
    columns aligned but labels and values in different boxes. Detecting that
    pairing gives label/value association across rows, which no amount of
    same-row geometry can supply.

Design rules
------------
* Every structure is derived, never stored over the raw observations. Raw
  OCR text, boxes and confidences remain the evidence of record.
* Every threshold is a named, documented, centrally adjustable constant.
* Nothing here decides a field value. These structures only constrain and
  explain candidate association; ambiguity is still reported as ambiguity.
"""

from app.document_intelligence.layout.columns import (
    ColumnModel,
    infer_columns,
)
from app.document_intelligence.layout.headers import (
    HeaderValueModel,
    detect_header_value_rows,
)
from app.document_intelligence.layout.sections import (
    SectionModel,
    infer_sections,
)
from app.document_intelligence.layout.structure import (
    PageStructure,
    build_page_structure,
)

__all__ = [
    "ColumnModel",
    "HeaderValueModel",
    "PageStructure",
    "SectionModel",
    "build_page_structure",
    "detect_header_value_rows",
    "infer_columns",
    "infer_sections",
]
