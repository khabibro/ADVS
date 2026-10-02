from dataclasses import dataclass, field

from app.core.errors import PROCESSING_ERROR_MESSAGES, ProcessingErrorCode


class OCRProviderError(Exception):
    """Raised by an OCRProvider. Always carries a taxonomy code so callers
    can distinguish OCR failure from an ambiguous/UNKNOWN document."""

    def __init__(self, code: ProcessingErrorCode, message: str | None = None) -> None:
        super().__init__(message or PROCESSING_ERROR_MESSAGES[code])
        self.code = code


@dataclass
class BoundingBox:
    """Source-space rectangle, origin top-left, x right, y down.

    OCR providers use pixels; embedded PDF text uses PDF points. The
    evidence reference records that coordinate space explicitly.
    """

    x: float
    y: float
    width: float
    height: float


@dataclass
class OCRLine:
    text: str
    confidence: float | None = None
    bounding_box: BoundingBox | None = None
    polygon: tuple[tuple[float, float], ...] | None = None
    detection_confidence: float | None = None
    orientation_degrees: float | None = None


@dataclass
class OCRPage:
    page_number: int
    text: str
    lines: list[OCRLine] = field(default_factory=list)
    confidence: float | None = None
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class OCRDocumentResult:
    """Provider-independent OCR output. Nothing downstream of this should
    touch raw provider response structures."""

    provider: str
    pages: list[OCRPage]
    assembled_text: str
    provider_request_id: str | None = None

    @property
    def page_count(self) -> int:
        return len(self.pages)
