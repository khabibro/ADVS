"""Which characters of a PDF text layer can a person actually see on the page?

A PDF stores text and drawing separately. Text can be invisible (render mode 3, which is what
an OCR'd "searchable PDF" uses), white on a white page, one point tall, off the page, or hidden
under an image, and a text extractor still returns it. Whoever builds the file can therefore make
the text layer say something different from what the reader sees. The pipeline treats embedded
text as exact, so a hidden "유효기간 2027-12-31" under a visible "2025-01-31" would be read as a
trusted value.

This module keeps only text that is visible, found two independent ways:

* the PDF's own flags (render mode 3, zero opacity, tiny font size, outside the page);
* a render test: the page is drawn once as it is and once with every text object removed. Text
  that changes no pixel under its own box is not visible (covers white-on-white, covered by an
  image, clipped).

Pages whose text cannot be trusted at all (unreadable font encoding, mostly picture, two
different texts on top of each other) are handed to OCR by the caller. Hidden text is never
used for extraction; its decision-relevant tokens are kept so the caller can compare them with
what OCR reads from the pixels.
"""

import re
from dataclasses import dataclass, field

import fitz
from PIL import Image, ImageChops

from app.document_intelligence.ocr.models import BoundingBox, OCRLine
from app.document_intelligence.ocr.text_assembly import order_lines

RENDER_SCALE = 1.5  # 108 dpi: enough to see 6 pt text change pixels
MIN_VISIBLE_FONT_SIZE = 2.0  # points; smaller text cannot be read by a person
CHANGED_PIXEL_LEVEL = 6  # grey-level difference that counts as drawn (faint watermarks are 10-20)
MIN_CHANGED_PIXELS = 2
GARBLED_RATIO = 0.3
HYBRID_IMAGE_SHARE = 0.25  # share of the page covered by pictures: text may live in the picture
OVERLAP_IOU = 0.6

# Tokens that can change a decision: dates and digit runs (business numbers, student numbers).
_DATE_TOKEN = re.compile(r"(?<!\d)(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})")
_DIGIT_RUN = re.compile(r"\d[\d\-\s]{5,}\d")
_PRIVATE_USE = re.compile("[-]")


@dataclass
class PageTextLayer:
    page_number: int
    lines: list[OCRLine]
    hidden_texts: list[str] = field(default_factory=list)
    hidden_reasons: set[str] = field(default_factory=set)
    garbled: bool = False
    hybrid: bool = False
    ambiguous: bool = False

    @property
    def hidden_tokens(self) -> set[str]:
        return decision_tokens(" ".join(self.hidden_texts))

    @property
    def trusted(self) -> bool:
        """False sends the page to OCR. Hidden text that carries a date or number is a possible
        manipulation, so such a page is read from its pixels even though the visible text is fine."""
        return not (self.garbled or self.hybrid or self.ambiguous or self.hidden_tokens)

    def reasons(self) -> list[str]:
        out = sorted(self.hidden_reasons) if self.hidden_tokens else []
        if self.garbled:
            out.append("garbled_font_encoding")
        if self.hybrid:
            out.append("image_regions")
        if self.ambiguous:
            out.append("overlapping_text")
        return out


def decision_tokens(text: str) -> set[str]:
    """Dates (as YYYY-MM-DD) and digit runs (digits only) found in `text`."""
    tokens = {f"{y}-{int(m):02d}-{int(d):02d}" for y, m, d in _DATE_TOKEN.findall(text)}
    for run in _DIGIT_RUN.findall(_DATE_TOKEN.sub(" ", text)):
        digits = re.sub(r"\D", "", run)
        if len(digits) >= 6:
            tokens.add(digits)
    return tokens


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("\xa0", " "))


def _is_garbled(text: str) -> bool:
    stripped = _norm(text)
    if len(stripped) < 10:
        return False
    bad = len(_PRIVATE_USE.findall(stripped)) + stripped.count("�")
    bad += 5 * stripped.count("(cid:")
    return bad / len(stripped) >= GARBLED_RATIO


def _substantial(text: str) -> bool:
    """Punctuation and stray marks may legitimately overlap; words and numbers may not."""
    return sum(character.isalnum() for character in text) >= 4


def _iou(a: fitz.Rect, b: fitz.Rect) -> float:
    inter = a & b
    if inter.is_empty:
        return 0.0
    area = inter.get_area()
    return area / (a.get_area() + b.get_area() - area)


def _render_gray(page: fitz.Page) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE), colorspace=fitz.csGRAY)
    return Image.frombytes("L", (pix.width, pix.height), pix.samples)


def _text_free_render(doc_bytes: bytes, index: int) -> Image.Image | None:
    try:
        with fitz.open(stream=doc_bytes, filetype="pdf") as copy:
            page = copy[index]
            page.add_redact_annot(page.rect, fill=False)
            page.apply_redactions(
                images=fitz.PDF_REDACT_IMAGE_NONE,
                graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                text=fitz.PDF_REDACT_TEXT_REMOVE,
            )
            return _render_gray(page)
    except (RuntimeError, ValueError, OSError):
        return None


def _drawn(full: Image.Image, bare: Image.Image, rect: fitz.Rect) -> bool:
    """True when removing all text changes pixels inside `rect`."""
    shrink = rect.height * 0.15
    box = (
        max(0, int(rect.x0 * RENDER_SCALE)),
        max(0, int((rect.y0 + shrink) * RENDER_SCALE)),
        min(full.width, int(rect.x1 * RENDER_SCALE) + 1),
        min(full.height, int((rect.y1 - shrink) * RENDER_SCALE) + 1),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        return False
    diff = ImageChops.difference(full.crop(box), bare.crop(box))
    changed = sum(diff.histogram()[CHANGED_PIXEL_LEVEL:])
    return changed >= MIN_CHANGED_PIXELS


def _flagged_invisible(page: fitz.Page) -> list[tuple[fitz.Rect, str, str]]:
    """Text objects the PDF itself marks as not drawn: (box, normalised text, reason)."""
    found = []
    for trace in page.get_texttrace():
        text = "".join(c[0] if isinstance(c[0], str) else chr(c[0]) for c in trace["chars"])
        reason = None
        if trace["type"] == 3:
            reason = "render_mode_invisible"
        elif trace.get("opacity", 1.0) < 0.05:
            reason = "zero_opacity"
        elif trace["size"] < MIN_VISIBLE_FONT_SIZE:
            reason = "tiny_font"
        elif not page.rect.intersects(fitz.Rect(trace["bbox"])):
            reason = "outside_page"
        if reason:
            found.append((fitz.Rect(trace["bbox"]), _norm(text), reason))
    return found


def analyse_page(doc_bytes: bytes, page: fitz.Page, page_number: int) -> PageTextLayer:
    flagged = _flagged_invisible(page)
    full = bare = None
    visible: list[OCRLine] = []
    visible_rects: list[tuple[fitz.Rect, str]] = []
    result = PageTextLayer(page_number, visible)
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            kept: list[str] = []
            kept_rects: list[fitz.Rect] = []
            for span in line.get("spans", []):
                text = str(span.get("text", ""))
                if not text.strip():
                    kept.append(text)
                    continue
                rect = fitz.Rect(span["bbox"])
                norm = _norm(text)
                reason = next(
                    (
                        why
                        for box, flagged_text, why in flagged
                        if _iou(rect, box) > 0.5 and (flagged_text == norm or norm in flagged_text)
                    ),
                    None,
                )
                if reason is None:
                    if full is None:
                        full = _render_gray(page)
                        bare = _text_free_render(doc_bytes, page_number - 1)
                    if bare is not None and not _drawn(full, bare, rect):
                        reason = "not_drawn"
                if reason:
                    result.hidden_texts.append(text)
                    result.hidden_reasons.add(reason)
                else:
                    kept.append(text)
                    kept_rects.append(rect)
                    visible_rects.append((rect, norm))
            source = "".join(kept).strip()
            if not source or not kept_rects:
                continue
            box = kept_rects[0]
            for other in kept_rects[1:]:
                box |= other
            visible.append(
                OCRLine(
                    text=source,
                    confidence=None,
                    bounding_box=BoundingBox(
                        x=box.x0, y=box.y0, width=box.width, height=box.height
                    ),
                )
            )
    result.lines = order_lines(visible)
    page_text = "\n".join(line.text for line in result.lines)
    result.garbled = _is_garbled(page_text)
    for i, (a, text_a) in enumerate(visible_rects):
        for b, text_b in visible_rects[i + 1 :]:
            if (
                text_a != text_b
                and _substantial(text_a)
                and _substantial(text_b)
                and _iou(a, b) > OVERLAP_IOU
            ):
                result.ambiguous = True
                break
        if result.ambiguous:
            break
    try:
        image_area = sum(fitz.Rect(info["bbox"]).get_area() for info in page.get_image_info())
        result.hybrid = (
            bool(page_text.strip())
            and image_area / max(page.rect.get_area(), 1) >= HYBRID_IMAGE_SHARE
        )
    except (RuntimeError, ValueError):
        result.hybrid = False
    return result


def pdf_provenance(doc: fitz.Document) -> dict:
    """Informational only: who produced the file. Never confirms a value."""
    meta = doc.metadata or {}
    signed = False
    try:
        signed = bool(doc.get_sigflags() > 0)
    except (RuntimeError, ValueError, AttributeError):
        signed = False
    return {
        "producer": meta.get("producer") or None,
        "creator": meta.get("creator") or None,
        "has_signature_fields": signed,
        "encrypted": bool(doc.is_encrypted),
    }


def audit_text_layer(embedded_pages: list, final_pages: list, provenance: dict) -> dict:
    """Summarise what happened to each PDF page's text layer.

    `embedded_pages` are the pages as PdfProcessor read them; `final_pages` are the pages the
    pipeline kept (embedded text where trusted, OCR otherwise). A page that was re-read by OCR
    while its hidden text carried dates or numbers is compared with the pixels: a hidden token
    that the OCR text does not contain is a mismatch (a possible manipulation).
    """
    final = {page.page_number: page for page in final_pages}
    pages: list[dict] = []
    mismatch = False
    for page in embedded_pages:
        layer = page.metadata.get("text_layer") or {}
        kept = final.get(page.page_number)
        used = (kept.metadata.get("source") if kept else None) or "ocr"
        entry: dict = {
            "page": page.page_number,
            "trusted": bool(layer.get("trusted", True)),
            "reasons": list(layer.get("reasons", [])),
            "text_used": "embedded" if used == "direct_pdf_text" else "ocr",
        }
        hidden = set(layer.get("hidden_tokens", []))
        if hidden and used != "direct_pdf_text" and kept is not None:
            unseen = sorted(hidden - decision_tokens(kept.text))
            if unseen:
                entry["hidden_tokens_not_on_page"] = unseen
                mismatch = True
        pages.append(entry)
    return {"provenance": provenance, "pages": pages, "mismatch": mismatch}
