from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image, ImageOps

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


class PdfProcessor:
    def extract_text(self, path: Path) -> PdfTextResult:
        with fitz.open(path) as doc:
            pages = [page.get_text("text") for page in doc]
            text = "\n".join(pages).strip()
            return PdfTextResult(len(doc), text, is_meaningful_text(text))


class ImagePreprocessor:
    def normalize(self, path: Path) -> Path:
        with Image.open(path) as img:
            ImageOps.exif_transpose(img).convert("RGB").save(path)
        return path
