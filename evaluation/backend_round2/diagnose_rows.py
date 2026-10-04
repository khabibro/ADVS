"""Stage-level diagnosis for one document: OCR lines -> rows -> candidates.

Answers "at which stage did this field die?" by materialising each
intermediate representation in turn, so the earliest stage that lost the
information is visible rather than inferred.

    cd apps/api
    ./.venv312/bin/python ../../evaluation/backend_round2/diagnose_rows.py \
        --filename "<Desktop filename>" --out ../../evaluation/backend_round2/work/diag.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "evaluation" / "backend_round2"))
from run_round2 import resolve_source  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filename", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--show-rows", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("OCR_PROVIDER", "paddle")
    os.environ.setdefault(
        "PADDLE_OCR_CACHE_DIR",
        str(REPO_ROOT / "apps" / "api" / "storage" / "paddleocr-cache"),
    )
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

    from app.core.config import get_settings
    from app.document_intelligence.extraction import base as ex_base
    from app.document_intelligence.ocr.layout import build_rows
    from app.document_intelligence.ocr.models import OCRDocumentResult
    from app.document_intelligence.ocr.providers import get_ocr_provider
    from app.document_intelligence.ocr.text_assembly import order_lines
    from app.document_intelligence.preprocessing.processor import PdfProcessor

    settings = get_settings()
    path = resolve_source(args.filename)
    is_pdf = path.suffix.lower() == ".pdf"

    pages = []
    if is_pdf:
        embedded = PdfProcessor().extract_text(path)
        pages = [p for p in embedded.pages]
        if not any(len(p.text.strip()) for p in pages):
            pages = []
    if not pages:
        import anyio

        pages = anyio.run(
            lambda: get_ocr_provider(settings).extract_document(
                path, "application/pdf" if is_pdf else "image/png", path.name
            )
        )

    result = OCRDocumentResult(
        provider="direct_pdf_text" if is_pdf else "paddle",
        pages=pages,
        assembled_text="\n\n".join(p.text for p in pages),
    )

    payload: dict = {"filename": unicodedata.normalize("NFC", path.name), "pages": []}
    for page in pages:
        ordered = order_lines(page.lines)
        rows = build_rows(page)
        payload["pages"].append(
            {
                "page_number": page.page_number,
                "char_count": len(page.text),
                "line_count": len(page.lines),
                "render_dpi": page.metadata.get("render_dpi"),
                "mean_confidence": page.confidence,
                "rows": [
                    {
                        "index": index,
                        "text": row.text,
                        "segment_count": len(row.segments),
                        "segment_texts": [s.text for s in row.segments],
                    }
                    for index, row in enumerate(rows)
                ],
                "raw_lines": [
                    {
                        "text": line.text,
                        "confidence": line.confidence,
                        "bbox": (
                            {
                                "x": line.bounding_box.x,
                                "y": line.bounding_box.y,
                                "w": line.bounding_box.width,
                                "h": line.bounding_box.height,
                            }
                            if line.bounding_box
                            else None
                        ),
                    }
                    for line in page.lines
                ],
            }
        )

    # Candidate generation is the next stage: show what each field's label set
    # actually matched, including rejected candidates, so a rejection is
    # distinguishable from "the label was never found".
    from app.document_intelligence.extraction.registry import _EXTRACTORS

    payload["candidates"] = {}
    for document_type, extractor in _EXTRACTORS.items():
        entry: dict = {}
        for field_name in _field_names(extractor):
            try:
                cands = ex_base.rank_candidates(result, extractor.LABELS.get(field_name, []), field_name)
            except Exception as exc:  # noqa: BLE001
                entry[field_name] = {"error": f"{type(exc).__name__}: {exc}"}
                continue
            entry[field_name] = [
                {
                    "value": c.value.value,
                    "score": round(c.score, 2),
                    "explicit_separator": c.has_explicit_separator,
                    "from_other_segment": c.value_from_other_segment,
                    "evidence": [
                        (e.bounding_box.x, e.bounding_box.y, e.text)
                        if e.bounding_box
                        else (None, None, e.text)
                        for e in c.evidence
                    ],
                }
                for c in cands[:5]
            ]
        payload["candidates"][document_type.value] = entry

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.show_rows:
        for page in payload["pages"]:
            print(f"--- page {page['page_number']} rows ---")
            for row in page["rows"]:
                print(f"  [{row['index']:3d}] segs={row['segment_count']} {row['text']!r}")


def _field_names(extractor: object) -> list[str]:
    """Best-effort list of the fields an extractor declares labels for."""
    labels = getattr(extractor, "LABELS", None)
    if isinstance(labels, dict):
        return list(labels)
    return []


if __name__ == "__main__":
    main()
