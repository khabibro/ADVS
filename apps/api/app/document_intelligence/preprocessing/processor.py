from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image, ImageOps

from app.core.errors import ProcessingErrorCode
from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage, OCRProviderError

# Below this character count, extracted "text" is typically stray metadata,
# watermarks, or noise rather than a usable text layer -- OCR is needed.
MIN_MEANINGFUL_TEXT_CHARS = 30


def is_meaningful_text(text: str) -> bool:
    stripped = text.strip()
    meaningful_characters = sum(character.isalnum() for character in stripped)
    return len(stripped) >= MIN_MEANINGFUL_TEXT_CHARS and meaningful_characters >= 15


@dataclass
class PdfTextResult:
    page_count: int
    text: str
    has_meaningful_text: bool
    pages: list[OCRPage]


class PdfProcessor:
    def extract_text(self, path: Path) -> PdfTextResult:
        try:
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
                            metadata={
                                "source": "direct_pdf_text",
                                "coordinate_space": "pdf_point",
                                "width": page.rect.width,
                                "height": page.rect.height,
                                "transform": {"pdf_rotation_degrees": page.rotation},
                            },
                        )
                    )
                text = "\n\n".join(page.text for page in pages).strip()
                return PdfTextResult(len(doc), text, is_meaningful_text(text), pages)
        except (fitz.FileDataError, RuntimeError, OSError) as exc:
            raise OCRProviderError(ProcessingErrorCode.CORRUPT_DOCUMENT) from exc


class ImagePreprocessor:
    """Prepares an uploaded image for the OCR engine, changing nothing else.

    Two jobs, both correctness rather than enhancement:

    * **EXIF orientation.** It is a declaration of how the pixels are meant to
      be displayed. Neither Pillow's `Image.open` nor the OpenCV loader behind
      PaddleOCR applies it, so a phone capture tagged orientation=6 reaches
      the detector sideways.
    * **Codec.** PaddleOCR accepts only a fixed set of image suffixes
      (jpg/jpeg/png/bmp). A perfectly ordinary `.webp` -- what browsers and
      most Android capture and share flows produce -- is otherwise unreadable
      and yields an empty OCR result.

    Deskew, denoising, contrast stretching and binarisation are a different
    category: each can improve one capture and damage the next. Measured skew
    across the real-document rounds stayed far below the threshold where
    correction helps, so none of them are here. They would be a regression
    waiting to happen if wired in globally without evidence.

    The result is written to `output_dir` rather than over the stored file, so
    the bytes ADVS keeps -- and the upload checksum derived from them -- are
    untouched. `prepare` returns None when the file already needs nothing.
    """

    #: EXIF tag 274. 1 (or absent) means the pixels are already upright.
    ORIENTATION_TAG = 274
    _UPRIGHT = 1
    #: Suffixes PaddleOCR reads without conversion.
    OCR_NATIVE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".bmp"})

    def needs_preparation(self, path: Path) -> bool:
        if path.suffix.lower() not in self.OCR_NATIVE_SUFFIXES:
            return True
        try:
            with Image.open(path) as img:
                orientation = int(img.getexif().get(self.ORIENTATION_TAG, self._UPRIGHT))
                return orientation != self._UPRIGHT
        except (OSError, ValueError) as exc:
            raise OCRProviderError(ProcessingErrorCode.CORRUPT_DOCUMENT) from exc

    def prepare(self, path: Path, output_dir: Path) -> Path | None:
        """Write a corrected, OCR-readable copy into `output_dir`, or return
        None when the file needs no change."""
        try:
            with Image.open(path) as img:
                output_dir.mkdir(parents=True, exist_ok=True)
                target = output_dir / f"{path.stem}.png"
                ImageOps.exif_transpose(img).convert("RGB").save(target)
        except (OSError, ValueError) as exc:
            raise OCRProviderError(ProcessingErrorCode.CORRUPT_DOCUMENT) from exc
        return target
