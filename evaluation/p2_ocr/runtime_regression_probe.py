"""Real Paddle provider concurrency and multipage probe; emits no OCR text."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "evaluation" / "p1_layout"))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("PADDLE_OCR_CACHE_DIR", str(ROOT / "apps/api/storage/paddleocr-cache"))

from app.core.config import Settings
from app.document_intelligence.ocr.providers import PaddleOCRProvider
from dataset_inventory import collect, detect_mime


async def run(private_dir: Path, multipage_dir: Path) -> dict[str, Any]:
    provider = PaddleOCRProvider(Settings(ocr_provider="paddle"))
    samples = collect(private_dir)

    async def process(sample: Any) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            pages = await provider.extract_document(sample.path, detect_mime(sample.path))
            return {
                "status": "COMPLETED",
                "pages": len(pages),
                "lines": sum(len(page.lines) for page in pages),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": type(exc).__name__,
                "pages": 0,
                "lines": 0,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
            }

    concurrent = await asyncio.gather(*(process(sample) for sample in samples[:2]))
    multipage: dict[str, Any] = {}
    for count in (1, 3, 6):
        path = multipage_dir / f"mp_{count}_0.pdf"
        result = await process(type("Sample", (), {"path": path})())
        multipage[str(count)] = result
    return {
        "schema_version": "p2-runtime-regression-v1",
        "provider": "PaddleOCR",
        "device": "cpu",
        "concurrent_distinct_documents": concurrent,
        "multipage": multipage,
        "ocr_text_persisted": False,
        "ocr_text_printed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", required=True, type=Path)
    parser.add_argument("--multipage-dir", required=True, type=Path)
    args = parser.parse_args()
    result = asyncio.run(run(args.private_dir, args.multipage_dir))
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
