"""P1 structural failure reproduction.

For every corpus document this records, per page:
  * the OCR observation geometry actually available,
  * the row structure the current pipeline derives,
  * the candidate set generated for each evaluated field,
  * why the field resolved or abstained.

Raw text, coordinates and candidate values go to the ignored private runtime
directory. The summarised structural findings go to stdout and to the report.

This reads the private corpus read-only through the real production OCR
provider. It does not modify production code and does not touch the
authoritative processing path.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import unicodedata
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

os.environ.setdefault("PADDLE_OCR_CACHE_DIR", str(REPO_ROOT / "apps/api/storage/paddleocr-cache"))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.config import Settings  # noqa: E402
from app.document_intelligence.classification.classifier import DocumentClassifier  # noqa: E402
from app.document_intelligence.extraction.base import (  # noqa: E402
    ExtractionInput,
    _source_observations,
    candidate_after_label,
    rank_candidates,
)
from app.document_intelligence.extraction.fields import FIELD_KINDS  # noqa: E402
from app.document_intelligence.extraction.registry import ExtractorRegistry  # noqa: E402
from app.document_intelligence.ocr.layout import build_rows  # noqa: E402
from app.document_intelligence.ocr.models import OCRDocumentResult, OCRLine  # noqa: E402
from app.document_intelligence.ocr.providers import get_ocr_provider  # noqa: E402
from app.document_intelligence.ocr.text_assembly import (  # noqa: E402
    assemble_document_text,
    order_lines,
)

sys.path.insert(0, str(REPO_ROOT / "evaluation" / "p1_layout"))
from dataset_inventory import collect, discover_private_dir  # noqa: E402

ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


def mime_for(path: Path) -> str:
    if path.suffix == ".pdf":
        return "application/pdf"
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}[path.suffix]


def row_geometry(rows) -> list[dict[str, Any]]:
    """Structural facts about each derived row, with no text retained."""
    out = []
    for row in rows:
        boxes = [s.bounding_box for s in row.segments]
        if all(b is not None for b in boxes):
            left = min(b.x for b in boxes)  # type: ignore[union-attr]
            top = min(b.y for b in boxes)  # type: ignore[union-attr]
            right = max(b.x + b.width for b in boxes)  # type: ignore[union-attr]
            bottom = max(b.y + b.height for b in boxes)  # type: ignore[union-attr]
            gaps = [
                round(boxes[i + 1].x - (boxes[i].x + boxes[i].width), 1)  # type: ignore[union-attr]
                for i in range(len(boxes) - 1)
            ]
        else:
            left = top = right = bottom = None
            gaps = []
        out.append(
            {
                "segments": len(row.segments),
                "has_geometry": row.has_geometry,
                "bbox": None if left is None else [round(left, 1), round(top, 1), round(right, 1), round(bottom, 1)],
                "inter_segment_gaps": gaps,
                "mean_height": round(
                    sum(b.height for b in boxes if b) / max(len([b for b in boxes if b]), 1), 1
                ),
            }
        )
    return out


def column_profile(rows, page_width: float | None) -> dict[str, Any]:
    """How much the 1-D row model conflates horizontally separated content.

    The current pipeline has no column concept: anything sharing a baseline is
    one row. A wide gap inside a row is therefore the observable signature of
    multiple logical columns having been merged.
    """
    wide_gaps = 0
    widest = 0.0
    multi_segment = 0
    for row in rows:
        boxes = [s.bounding_box for s in row.segments]
        if len(boxes) < 2:
            continue
        multi_segment += 1
        for i in range(len(boxes) - 1):
            if boxes[i] is None or boxes[i + 1] is None:  # type: ignore[union-attr]
                continue
            gap = boxes[i + 1].x - (boxes[i].x + boxes[i].width)  # type: ignore[union-attr]
            widest = max(widest, gap)
            reference = max(min(boxes[i].height, boxes[i + 1].height), 1.0)  # type: ignore[union-attr]
            if gap > reference:
                wide_gaps += 1
    return {
        "page_width": None if page_width is None else round(page_width, 1),
        "rows": len(rows),
        "multi_segment_rows": multi_segment,
        "intra_row_gaps_wider_than_line_height": wide_gaps,
        "widest_intra_row_gap": round(widest, 1),
        "has_column_concept": False,
    }


async def analyse_document(sample, provider) -> dict[str, Any]:
    pages = await provider.extract_document(sample.path, mime_for(sample.path))
    for page in pages:
        if page.metadata.get("source") != "direct_pdf_text":
            page.metadata.setdefault("source", "ocr")
    pages.sort(key=lambda page: page.page_number)
    # Assemble exactly the way DocumentProcessingService does, so the probe
    # measures the production representation and not a convenient variant.
    result = OCRDocumentResult(
        provider=provider.provider_name,
        pages=pages,
        assembled_text=assemble_document_text(pages),
    )
    pages_out = []
    for page in result.pages:
        ordered = order_lines(page.lines)
        rows = build_rows(
            type(page)(
                page_number=page.page_number,
                text=page.text,
                lines=ordered,
                confidence=page.confidence,
                duration_ms=page.duration_ms,
                metadata=page.metadata,
            )
        )
        boxes = [l.bounding_box for l in page.lines if l.bounding_box]
        page_width = max((b.x + b.width for b in boxes), default=None)
        pages_out.append(
            {
                "page_number": page.page_number,
                "line_count": len(page.lines),
                "lines_with_geometry": len(boxes),
                "char_count": len(page.text),
                "mean_confidence": page.confidence,
                "render_dpi": page.metadata.get("render_dpi"),
                "render_scale": (page.metadata.get("transform") or {}).get("render_scale"),
                "render_scale_reason": (page.metadata.get("transform") or {}).get("render_scale_reason"),
                "source": page.metadata.get("source", result.provider),
                "row_profile": column_profile(rows, page_width),
                "rows": row_geometry(rows),
            }
        )

    classification = DocumentClassifier().classify(result.assembled_text)
    observations = _source_observations(result)
    record: dict[str, Any] = {
        "sample_id": sample.sample_id,
        "sha256": sample.sha256,
        "pages": pages_out,
        "total_rows": len(observations),
        "classification": {
            "document_type": classification.predicted_type.value,
            "confidence": classification.confidence_score,
            "needs_review": classification.needs_review,
            "evidence_count": len(classification.evidence),
        },
    }

    # Per-field candidate introspection, including fields that abstained.
    registry = ExtractorRegistry()
    extractor = registry.get(classification.predicted_type)
    field_records: dict[str, Any] = {}
    if extractor is not None:
        for extracted in extractor.extract(result):
            field_records[extracted.field_name] = {
                "extracted": extracted.normalized_value is not None,
                "needs_review": extracted.needs_review,
                "method": extracted.extraction_method,
                "confidence": extracted.confidence,
                "evidence_count": len(extracted.evidence or []),
                "evidence_pages": sorted({e.page_number for e in (extracted.evidence or [])}),
                "evidence_kinds": sorted({e.source_kind for e in (extracted.evidence or [])}),
            }
    record["fields"] = field_records
    record["observation_dump"] = {
        "rows": [
            {
                "page_number": obs.row.page_number,
                "segment_count": len(obs.row.segments),
                "segments": [
                    {
                        "text": seg.text,
                        "confidence": seg.confidence,
                        "bbox": None
                        if seg.bounding_box is None
                        else [
                            round(seg.bounding_box.x, 1),
                            round(seg.bounding_box.y, 1),
                            round(seg.bounding_box.width, 1),
                            round(seg.bounding_box.height, 1),
                        ],
                    }
                    for seg in obs.row.segments
                ],
            }
            for obs in observations
        ]
    }
    return record


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", default=None)
    parser.add_argument("--out", default=str(REPO_ROOT / "evaluation/private_runtime/p1_structural_dump.json"))
    parser.add_argument("--summary", default=str(REPO_ROOT / "evaluation/private_runtime/p1_structural_summary.json"))
    args = parser.parse_args()

    private_dir = discover_private_dir(args.private_dir)
    if private_dir is None:
        print("private directory not found")
        return 2
    samples = collect(private_dir)
    provider = get_ocr_provider(Settings(ocr_provider="paddle"))

    dump: list[dict[str, Any]] = []
    for sample in samples:
        print(f"analysing {sample.sample_id} ...", flush=True)
        dump.append(await analyse_document(sample, provider))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = []
    for record in dump:
        pages = record["pages"]
        merged = sum(p["row_profile"]["intra_row_gaps_wider_than_line_height"] for p in pages)
        widest = max((p["row_profile"]["widest_intra_row_gap"] for p in pages), default=0.0)
        summary.append(
            {
                "sample_id": record["sample_id"],
                "pages": len(pages),
                "classification": record["classification"]["document_type"],
                "classification_needs_review": record["classification"]["needs_review"],
                "total_rows": record["total_rows"],
                "mean_row_segments": round(
                    sum(p["row_profile"]["multi_segment_rows"] for p in pages)
                    / max(len(pages), 1),
                    2,
                ),
                "intra_row_gaps_wider_than_line_height": merged,
                "widest_intra_row_gap": widest,
                "fields_extracted": sum(1 for f in record["fields"].values() if f["extracted"]),
                "fields_total": len(record["fields"]),
                "render_scale": pages[0]["render_scale"] if pages else None,
                "render_scale_reason": pages[0]["render_scale_reason"] if pages else None,
            }
        )
    Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"{'sample':10} {'pages':>5} {'rows':>5} {'merged':>7} {'widest':>8} {'cls':<34} {'fields':>7}")
    for item in summary:
        print(
            f"{item['sample_id']:10} {item['pages']:>5} {item['total_rows']:>5} "
            f"{item['intra_row_gaps_wider_than_line_height']:>7} {item['widest_intra_row_gap']:>8} "
            f"{item['classification']:<34} "
            f"{str(item['fields_extracted']) + '/' + str(item['fields_total']):>7}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))