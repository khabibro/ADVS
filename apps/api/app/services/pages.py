"""Page images and normalised evidence boxes, so the web app can show where a value was read.

Boxes are returned as fractions (0..1) of the page, which is independent of the resolution the
page image is served at. A box is only returned when the coordinate system it was recorded in is
known exactly; otherwise it is omitted rather than guessed.
"""

import io
import math
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageOps

from app.core.config import get_settings
from app.models.entities import Document
from app.schemas.api import BoundingBoxRead, PageInfoRead
from app.services.storage.local import LocalStorageService

PDF_SERVE_SCALE = 2.0  # 144 DPI
MAX_IMAGE_SIDE = 1800


def _path(document: Document) -> Path:
    return LocalStorageService(get_settings()).path_for(document.storage_key)


def _is_pdf(document: Document) -> bool:
    return document.mime_type == "application/pdf"


def _served_image_size(width: int, height: int) -> tuple[int, int]:
    factor = min(1.0, MAX_IMAGE_SIDE / max(width, height))
    return max(1, round(width * factor)), max(1, round(height * factor))


def page_infos(document: Document) -> list[PageInfoRead]:
    path = _path(document)
    if _is_pdf(document):
        with fitz.open(path) as pdf:
            return [
                PageInfoRead(
                    page_number=index,
                    width=math.ceil(page.rect.width * PDF_SERVE_SCALE),
                    height=math.ceil(page.rect.height * PDF_SERVE_SCALE),
                )
                for index, page in enumerate(pdf, start=1)
            ]
    with Image.open(path) as image:
        oriented = ImageOps.exif_transpose(image)
        width, height = _served_image_size(*oriented.size)
    return [PageInfoRead(page_number=1, width=width, height=height)]


def render_page_png(document: Document, page_number: int) -> bytes | None:
    path = _path(document)
    if _is_pdf(document):
        with fitz.open(path) as pdf:
            if not 1 <= page_number <= pdf.page_count:
                return None
            pixmap = pdf[page_number - 1].get_pixmap(
                matrix=fitz.Matrix(PDF_SERVE_SCALE, PDF_SERVE_SCALE), alpha=False
            )
            return pixmap.tobytes("png")
    if page_number != 1:
        return None
    with Image.open(path) as image:
        oriented = ImageOps.exif_transpose(image).convert("RGB")
        oriented = oriented.resize(_served_image_size(*oriented.size))
        buffer = io.BytesIO()
        oriented.save(buffer, format="PNG")
        return buffer.getvalue()


class EvidenceBoxNormalizer:
    """Normalises the evidence boxes of one document (opens the file at most once)."""

    def __init__(self, document: Document) -> None:
        self.document = document
        self._pdf_points: dict[int, tuple[float, float]] | None = None

    def _points(self) -> dict[int, tuple[float, float]]:
        if self._pdf_points is None:
            with fitz.open(_path(self.document)) as pdf:
                self._pdf_points = {
                    index: (page.rect.width, page.rect.height)
                    for index, page in enumerate(pdf, start=1)
                }
        return self._pdf_points

    def normalize(self, evidence: dict[str, Any]) -> BoundingBoxRead | None:
        box = evidence.get("bounding_box")
        if not box or not self.document.mime_type:
            return None
        transform = evidence.get("transform") or {}
        if transform.get("pdf_rotation_degrees", 0) not in (0, None):
            return None
        try:
            width = height = 0.0
            if _is_pdf(self.document):
                size = self._points().get(int(evidence.get("page_number", 1)))
                if size is None:
                    return None
                if evidence.get("coordinate_space") == "pdf_point":
                    width, height = size
                else:
                    scale = transform.get("render_scale")
                    if not scale:
                        return None
                    width, height = size[0] * float(scale), size[1] * float(scale)
            else:
                if int(transform.get("exif_orientation") or 1) != 1:
                    return None
                width = float(transform.get("source_width") or 0)
                height = float(transform.get("source_height") or 0)
            if width <= 0 or height <= 0:
                return None
            x = min(max(box["x"] / width, 0.0), 1.0)
            y = min(max(box["y"] / height, 0.0), 1.0)
            return BoundingBoxRead(
                x=x,
                y=y,
                width=min(box["width"] / width, 1.0 - x),
                height=min(box["height"] / height, 1.0 - y),
            )
        except (KeyError, TypeError, ValueError, OSError, RuntimeError):
            return None
