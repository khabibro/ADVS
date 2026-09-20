from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image, ImageOps

from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage

# Below this character count, extracted "text" is typically stray metadata,
# watermarks, or noise rather than a usable text layer -- OCR is needed.
MIN_MEANINGFUL_TEXT_CHARS = 30


def is_meaningful_text(text: str) -> bool:
    return len(text.strip()) >= MIN_MEANINGFUL_TEXT_CHARS


@dataclass
class PdfTextResult:
    page_count: int
    text: str
    has_meaningful_text: bool
    pages: list[OCRPage]


class PdfProcessor:
    def extract_text(self, path: Path) -> PdfTextResult:
        with fitz.open(path) as doc:
            pages: list[OCRPage] = []
            for page_number, page in enumerate(doc, start=1):
                lines: list[OCRLine] = []
                for block in page.get_text("dict").get("blocks", []):
                    for line in block.get("lines", []):
                        spans = line.get("spans", [])
                        source = "".join(str(span.get("text", "")) for span in spans).strip()
                        bbox = line.get("bbox")
                        if not source:
                            continue
                        box = None
                        if bbox and len(bbox) == 4:
                            x1, y1, x2, y2 = (float(value) for value in bbox)
                            box = BoundingBox(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
                        lines.append(OCRLine(text=source, confidence=None, bounding_box=box))
                page_text = "\n".join(line.text for line in lines)
                pages.append(
                    OCRPage(
                        page_number=page_number,
                        text=page_text,
                        lines=lines,
                        confidence=None,
                        metadata={"source": "direct_pdf_text"},
                    )
                )
            text = "\n\n".join(page.text for page in pages).strip()
            return PdfTextResult(len(doc), text, is_meaningful_text(text), pages)


class ImagePreprocessor:
    def normalize(self, path: Path) -> Path:
        with Image.open(path) as img:
            ImageOps.exif_transpose(img).convert("RGB").save(path)
        return path
