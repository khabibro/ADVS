"""Renders synthetic gold text into an actual file (PDF/PNG/JPEG).

Uses only PyMuPDF and Pillow, both already project dependencies -- no
OpenCV or other heavy CV library is introduced.

IMPORTANT HONESTY NOTE: the evaluation runner's default ("mock") mode scores
classification/extraction/validation against the *gold text* directly, not
by actually running OCR against these rendered files (there is no local OCR
engine to do that with). These rendered files exist so the dataset has real
file-format/quality coverage and so PaddleOCR evaluation has
something real to send. Quality/format metadata is recorded per sample, but
it does not currently affect mock-mode metrics -- see evaluation/README.md.
"""

import io
from dataclasses import dataclass

import fitz
from PIL import Image, ImageEnhance, ImageFilter

PAGE_WIDTH, PAGE_HEIGHT = 595, 842  # A4 at 72dpi
FONT_SIZE = 12
LINE_HEIGHT = 20
MARGIN_LEFT = 60
MARGIN_TOP = 80

# PyMuPDF bundles a Korean CJK font ("korea-s") specifically for this
# purpose -- no external font file is needed.
CJK_FONT = "korea-s"


def _build_pdf(lines: list[str]) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = MARGIN_TOP
    for line in lines:
        page.insert_text(
            (MARGIN_LEFT, y),
            line,
            fontsize=FONT_SIZE,
            fontname=CJK_FONT,
            encoding=fitz.TEXT_ENCODING_LATIN,
        )
        y += LINE_HEIGHT
    return doc


@dataclass
class RenderedDocument:
    input_format: str
    quality: str
    extension: str
    content: bytes


def render(lines: list[str], input_format: str, quality: str, rng_seed: int) -> RenderedDocument:
    """input_format: text_pdf | scanned_pdf | png | jpg
    quality: clean | compressed | blurred | low_contrast | rotated | low_resolution
    """
    doc = _build_pdf(lines)
    try:
        if input_format == "text_pdf":
            # Real embedded text layer -- PdfProcessor will extract it
            # directly and OCR is never invoked for this sample.
            return RenderedDocument(input_format, "clean", "pdf", doc.tobytes())

        page = doc[0]
        pixmap = page.get_pixmap(dpi=100)
        image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
        image = _apply_quality(image, quality, rng_seed)

        if input_format == "scanned_pdf":
            image_doc = fitz.open()
            image_page = image_doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            buf = io.BytesIO()
            image.save(buf, format="JPEG", quality=85)
            image_page.insert_image(image_page.rect, stream=buf.getvalue())
            content = image_doc.tobytes()
            image_doc.close()
            return RenderedDocument(input_format, quality, "pdf", content)

        buf = io.BytesIO()
        if input_format == "jpg":
            jpeg_quality = 75 if quality == "compressed" else 92
            image.save(buf, format="JPEG", quality=jpeg_quality)
            return RenderedDocument(input_format, quality, "jpg", buf.getvalue())

        if input_format == "png":
            image.save(buf, format="PNG")
            return RenderedDocument(input_format, quality, "png", buf.getvalue())

        raise ValueError(f"unsupported input_format: {input_format}")
    finally:
        doc.close()


def _apply_quality(image: Image.Image, quality: str, rng_seed: int) -> Image.Image:
    if quality == "clean" or quality == "compressed":
        return image
    if quality == "blurred":
        return image.filter(ImageFilter.GaussianBlur(radius=1.5))
    if quality == "low_contrast":
        return ImageEnhance.Contrast(image).enhance(0.5)
    if quality == "rotated":
        angle = 1.5 if rng_seed % 2 == 0 else -1.5
        return image.rotate(angle, expand=False, fillcolor=(255, 255, 255))
    if quality == "low_resolution":
        small = image.resize((image.width // 2, image.height // 2))
        return small.resize((image.width, image.height))
    return image
