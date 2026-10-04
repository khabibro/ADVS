"""Reconstruct the production extraction input from a cached OCR dump.

OCR is by far the slowest step and it is deterministic for a given model cache,
so the benchmark captures observations once and every architecture candidate
replays the *same* observations. That is what makes an architecture comparison
fair: identical text, identical geometry, identical confidences, differing only
in the structural layer under test.

The dump is written to the ignored private runtime directory and never
committed.
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

os.environ.setdefault("PADDLE_OCR_CACHE_DIR", str(REPO_ROOT / "apps/api/storage/paddleocr-cache"))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.document_intelligence.ocr.models import (  # noqa: E402
    BoundingBox,
    OCRDocumentResult,
    OCRLine,
    OCRPage,
)
from app.document_intelligence.ocr.text_assembly import assemble_document_text  # noqa: E402

DEFAULT_DUMP = Path("/var/folders/yb/qd_ktv9s0m37gmwmskgmzh5m0000gn/T/opencode/advs/p1_observations.json")


def capture(private_dir: Path, out: Path) -> Path:
    """Run the real OCR provider once and store observations."""
    import asyncio

    sys.path.insert(0, str(REPO_ROOT / "evaluation" / "p1_layout"))
    from dataset_inventory import collect, detect_mime  # noqa: PLC0415

    from app.core.config import Settings  # noqa: PLC0415
    from app.document_intelligence.ocr.providers import get_ocr_provider  # noqa: PLC0415

    provider = get_ocr_provider(Settings(ocr_provider="paddle"))
    samples = collect(private_dir)

    async def run() -> dict[str, Any]:
        captured: dict[str, Any] = {}
        for sample in samples:
            pages = await provider.extract_document(sample.path, detect_mime(sample.path))
            captured[sample.sample_id] = [
                {
                    "page_number": page.page_number,
                    "text": page.text,
                    "confidence": page.confidence,
                    "duration_ms": page.duration_ms,
                    "metadata": page.metadata,
                    "lines": [
                        {
                            "text": line.text,
                            "confidence": line.confidence,
                            "detection_confidence": line.detection_confidence,
                            "orientation_degrees": line.orientation_degrees,
                            "polygon": None
                            if line.polygon is None
                            else [list(point) for point in line.polygon],
                            "bbox": None
                            if line.bounding_box is None
                            else {
                                "x": line.bounding_box.x,
                                "y": line.bounding_box.y,
                                "width": line.bounding_box.width,
                                "height": line.bounding_box.height,
                            },
                        }
                        for line in page.lines
                    ],
                }
                for page in pages
            ]
            print(f"  captured {sample.sample_id}", flush=True)
        return captured

    captured = asyncio.run(run())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(captured, ensure_ascii=False), encoding="utf-8")
    return out


def load(dump: Path | None = None) -> dict[str, OCRDocumentResult]:
    """Rebuild OCRDocumentResult objects exactly as processing.py would."""
    path = dump or DEFAULT_DUMP
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out: dict[str, OCRDocumentResult] = {}
    for sample_id, page_dicts in raw.items():
        pages: list[OCRPage] = []
        for page_dict in page_dicts:
            lines = [
                OCRLine(
                    text=item["text"],
                    confidence=item["confidence"],
                    bounding_box=None
                    if item["bbox"] is None
                    else BoundingBox(**item["bbox"]),
                    polygon=None
                    if item["polygon"] is None
                    else tuple(tuple(point) for point in item["polygon"]),
                    detection_confidence=item.get("detection_confidence"),
                    orientation_degrees=item.get("orientation_degrees"),
                )
                for item in page_dict["lines"]
            ]
            metadata = dict(page_dict.get("metadata") or {})
            metadata.setdefault("source", "ocr")
            pages.append(
                OCRPage(
                    page_number=page_dict["page_number"],
                    text=page_dict["text"],
                    lines=lines,
                    confidence=page_dict.get("confidence"),
                    duration_ms=page_dict.get("duration_ms", 0),
                    metadata=metadata,
                )
            )
        pages.sort(key=lambda page: page.page_number)
        out[sample_id] = OCRDocumentResult(
            provider="paddle",
            pages=pages,
            assembled_text=assemble_document_text(pages),
        )
    return out


def page_dicts_placeholder(page_dict: dict[str, Any]) -> list[dict[str, Any]]:
    return page_dict["lines"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", default=os.environ.get("ADVS_PRIVATE_DIR"))
    parser.add_argument("--out", default=str(DEFAULT_DUMP))
    args = parser.parse_args()

    sys.path.insert(0, str(REPO_ROOT / "evaluation" / "p1_layout"))
    from dataset_inventory import discover_private_dir  # noqa: PLC0415

    directory = discover_private_dir(args.private_dir)
    if directory is None:
        raise SystemExit("private document directory not found")
    path = capture(directory, Path(args.out))
    print(f"observations written to {path}")