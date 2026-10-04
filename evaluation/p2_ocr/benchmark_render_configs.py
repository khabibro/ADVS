"""Compare PDF render-DPI OCR output without persisting or printing OCR text."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "evaluation" / "p1_layout"))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("PADDLE_OCR_CACHE_DIR", str(ROOT / "apps/api/storage/paddleocr-cache"))

from app.core.config import Settings
from app.document_intelligence.ocr.providers import PaddleOCRProvider
from dataset_inventory import collect, detect_mime, discover_private_dir


def _summary(pages: list[Any], baseline_pages: list[dict[str, Any]] | None) -> dict[str, Any]:
    text = [page.text for page in pages]
    line_text = [[line.text for line in page.lines] for page in pages]
    baseline_text = None if baseline_pages is None else [page["text"] for page in baseline_pages]
    baseline_lines = (
        None
        if baseline_pages is None
        else [[line["text"] for line in page["lines"]] for page in baseline_pages]
    )
    return {
        "pages": len(pages),
        "lines": sum(len(page.lines) for page in pages),
        "lines_with_bbox": sum(
            1 for page in pages for line in page.lines if line.bounding_box is not None
        ),
        "duration_ms": sum(page.duration_ms for page in pages),
        "exact_page_text_match_vs_baseline": text == baseline_text,
        "exact_line_text_match_vs_baseline": line_text == baseline_lines,
    }


async def run(private_dir: Path, dpis: list[int], baseline_path: Path | None) -> dict[str, Any]:
    samples = [sample for sample in collect(private_dir) if sample.suffix == ".pdf"]
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path else {}
    results: dict[str, Any] = {}
    for dpi in dpis:
        provider = PaddleOCRProvider(
            Settings(
                ocr_provider="paddle",
                paddle_ocr_render_dpi=dpi,
                paddle_ocr_cache_dir=os.environ["PADDLE_OCR_CACHE_DIR"],
            )
        )
        per_document: dict[str, Any] = {}
        for sample in samples:
            pages = await provider.extract_document(sample.path, detect_mime(sample.path))
            baseline_pages = baseline.get(sample.sample_id)
            per_document[sample.sample_id] = _summary(pages, baseline_pages)
        results[str(dpi)] = per_document
    return {
        "schema_version": "p2-render-config-probe-v1",
        "documents": len(samples),
        "dpis": dpis,
        "results": results,
        "ocr_text_persisted": False,
        "ocr_text_printed": False,
        "correctness_scored": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", default=os.environ.get("ADVS_PRIVATE_DIR"))
    parser.add_argument("--dpis", default="200,288,300")
    parser.add_argument("--baseline-cache", type=Path)
    args = parser.parse_args()
    private_dir = discover_private_dir(args.private_dir)
    if private_dir is None:
        raise SystemExit("Private sample directory not found")
    dpis = [int(value) for value in args.dpis.split(",")]
    result = asyncio.run(run(private_dir, dpis, args.baseline_cache))
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
