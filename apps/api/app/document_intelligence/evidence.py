from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.document_intelligence.ocr.models import BoundingBox

EvidenceSourceKind = Literal["ocr", "embedded_pdf_text"]
CoordinateSpace = Literal["pixel", "pdf_point"]


@dataclass(frozen=True)
class EvidenceRef:
    """Provider-independent source observation supporting an extracted field.

    ``page_number`` is 1-based. Bounding boxes use pixel/page coordinates with
    a top-left origin and the existing ``x, y, width, height`` rectangle shape.
    Confidence is the source line confidence and is absent for direct PDF text.
    """

    page_number: int
    source_text: str
    bounding_box: BoundingBox | None = None
    confidence: float | None = None
    source_kind: EvidenceSourceKind = "ocr"
    coordinate_space: CoordinateSpace = "pixel"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
