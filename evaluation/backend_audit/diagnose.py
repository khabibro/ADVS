"""Read-only diagnostic for the real-document audit.

Runs the *production* source-selection + classification + extraction path on a
single local file and reports, stage by stage, where information is lost.
It writes nothing to the repository except JSON under
``evaluation/backend_audit/work/`` (gitignored), and never prints full OCR
text unless ``--show-text`` is passed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

import fitz  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.domain import DocumentType  # noqa: E402
from app.document_intelligence.classification.classifier import (  # noqa: E402
    DocumentClassifier,
)
from app.document_intelligence.extraction.registry import ExtractorRegistry  # noqa: E402
from app.document_intelligence.ocr.models import OCRProviderError  # noqa: E402
from app.document_intelligence.ocr.providers import PaddleOCRProvider  # noqa: E402
from app.document_intelligence.ocr.text_assembly import (  # noqa: E402
    assemble_document_text,
    order_lines,
)
from app.document_intelligence.preprocessing.processor import (  # noqa: E402
    PdfProcessor,
    is_meaningful_text,
)

WORK_DIR = REPO_ROOT / "evaluation" / "backend_audit" / "work"


def pdf_facts(path: Path) -> dict:
    with fitz.open(path) as doc:
        pages = []
        for page in doc:
            pages.append(
                {
                    "page": page.number,
                    "width_pt": round(page.rect.width, 1),
                    "height_pt": round(page.rect.height, 1),
                    "rotation": page.rotation,
                    "embedded_text_chars": len(page.get_text().strip()),
                    "image_count": len(page.get_images(full=True)),
                }
            )
        return {"page_count": doc.page_count, "pages": pages}


async def run(path: Path, show_text: bool) -> dict:
    report: dict = {"file": path.name, "pdf": pdf_facts(path)}
    settings = get_settings()
    report["provider_config"] = {
        "ocr_provider": settings.ocr_provider,
        "lang": settings.paddle_ocr_lang,
        "rec_model": settings.paddle_ocr_rec_model_name,
        "det_model": settings.paddle_ocr_det_model_name,
        "device": settings.paddle_ocr_device,
    }

    # --- Stage: embedded-text routing decision (production logic) ---------
    pdf = PdfProcessor()
    try:
        text_result = pdf.extract_text(path)
        report["routing"] = {
            "embedded_text_chars": len(text_result.text.strip()),
            "has_meaningful_text": text_result.has_meaningful_text,
            "decision": "EMBEDDED_TEXT" if text_result.has_meaningful_text else "OCR",
        }
    except OCRProviderError as exc:
        report["routing"] = {"error": str(exc.code)}
        text_result = None

    # --- Stage: OCR -------------------------------------------------------
    provider = PaddleOCRProvider(settings)
    started = time.perf_counter()
    try:
        pages = await provider.extract_document(path, "application/pdf", path.name)
    except OCRProviderError as exc:
        report["ocr"] = {"status": "FAILED", "code": str(exc.code), "message": str(exc)}
        return report
    ocr_ms = (time.perf_counter() - started) * 1000

    assembled = assemble_document_text(pages)
    report["ocr"] = {
        "status": "OK",
        "duration_ms": round(ocr_ms, 1),
        "page_count": len(pages),
        "line_count": sum(len(p.lines) for p in pages),
        "chars": len(assembled),
        "page_confidence": [p.confidence for p in pages],
        "line_confidence": {
            "min": min(
                (l.confidence for p in pages for l in p.lines if l.confidence is not None),
                default=None,
            ),
            "max": max(
                (l.confidence for p in pages for l in p.lines if l.confidence is not None),
                default=None,
            ),
            "mean": (
                sum(l.confidence for p in pages for l in p.lines if l.confidence is not None)
                / max(1, sum(1 for p in pages for l in p.lines if l.confidence is not None))
            ),
        },
        "empty_lines": sum(1 for p in pages for l in p.lines if not l.text.strip()),
    }
    if show_text:
        report["ocr"]["text"] = assembled

    # --- Stage: classification ------------------------------------------
    classifier = DocumentClassifier()
    # filename deliberately blanked: production passes original_filename, and
    # using it here would let the filename leak into the result.
    classification = classifier.classify(assembled, "")
    report["classification"] = {
        "predicted_type": str(classification.predicted_type),
        "confidence": classification.confidence_score,
        "score": classification.score,
        "evidence": classification.evidence,
        "needs_review": classification.needs_review,
        "alternatives": [
            {"type": str(a.document_type), "score": a.score}
            for a in classification.alternatives[:4]
        ],
    }
    # Filename-leakage probe: does passing the filename change the outcome?
    with_name = classifier.classify(assembled, path.name)
    report["classification"]["with_filename"] = {
        "predicted_type": str(with_name.predicted_type),
        "confidence": with_name.confidence_score,
    }

    # --- Stage: extraction ----------------------------------------------
    registry = ExtractorRegistry()
    from app.document_intelligence.ocr.models import OCRDocumentResult

    doc_result = OCRDocumentResult(
        provider="paddle",
        pages=pages,
        assembled_text=assembled,
    )
    fields = registry.extract(DocumentType(classification.predicted_type), doc_result)
    report["extraction"] = {
        "fields": [
            {
                "field": f.field_name,
                "populated": f.normalized_value is not None,
                "method": f.extraction_method,
                "confidence": f.confidence,
                "evidence_pages": sorted({e.page_number for e in (f.evidence or [])}),
                "evidence_kinds": sorted({e.source_kind for e in (f.evidence or [])}),
                "value_preview": (
                    f.normalized_value[:2] + "***" if f.normalized_value else None
                ),
            }
            for f in fields
        ]
    }

    # --- Stage: geometry diagnostics -------------------------------------
    geo = []
    for page in pages:
        boxes = [l.bounding_box for l in page.lines if l.bounding_box]
        if boxes:
            geo.append(
                {
                    "page": page.page_number,
                    "min_x": round(min(b.x for b in boxes), 1),
                    "min_y": round(min(b.y for b in boxes), 1),
                    "max_x": round(max(b.x + b.width for b in boxes), 1),
                    "max_y": round(max(b.y + b.height for b in boxes), 1),
                    "median_line_h": round(
                        sorted(b.height for b in boxes)[len(boxes) // 2], 1
                    ),
                }
            )
    report["geometry"] = geo

    # Reading-order check: is provider order already the assembled order?
    order_diffs = 0
    for page in pages:
        if [id(l) for l in order_lines(page.lines)] != [id(l) for l in page.lines]:
            order_diffs += 1
    report["reading_order"] = {"pages_reordered": order_diffs, "page_count": len(pages)}

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--show-text", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    report = asyncio.run(run(args.path, args.show_text))
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.show_text:
        print(payload)
    else:
        print(payload)
    out = args.out or (WORK_DIR / f"diagnose_{args.path.stem}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
