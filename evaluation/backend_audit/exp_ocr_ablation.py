"""Controlled OCR ablation harness for the backend audit.

Renders the same PDF page at several rasterization scales, runs the same
PaddleOCR model, and measures the properties that actually decide whether
the downstream (line-based) pipeline can work:

  * how many detected text boxes there are (fragmentation)
  * whether known Korean labels survive as contiguous substrings
  * OCR confidence
  * wall-clock cost

This is evaluation-only code. It does not import or modify production
modules' behaviour.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

import fitz  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.document_intelligence.ocr.providers import PaddleOCRProvider  # noqa: E402

WORK_DIR = REPO_ROOT / "evaluation" / "backend_audit" / "work"

# Labels that must be recoverable as contiguous substrings for the current
# line-based extractor to work at all. Derived from EXPECTED_FIELDS +
# each extractor's label list, not from this particular document.
REQUIRED_LABELS = [
    "재학증명서",
    "성명",
    "소속",
    "전공",
    "입학일자",
    "재학학년",
    "대학",
    "학번",
    "발급일",
]


def render(path: Path, scale: float, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with fitz.open(path) as doc:
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        target = out_dir / f"scale_{str(scale).replace('.', '_')}.png"
        pix.save(target)
        return target


def label_recovery(text: str) -> dict[str, bool]:
    squashed = "".join(text.split())
    return {label: label in squashed for label in REQUIRED_LABELS}


async def measure(image: Path, scale: float) -> dict:
    settings = get_settings()
    provider = PaddleOCRProvider(settings)
    started = time.perf_counter()
    pages = await provider.extract_document(image, "image/png", image.name)
    elapsed = (time.perf_counter() - started) * 1000
    lines = [line for page in pages for line in page.lines]
    text = "\n".join(line.text for line in lines)
    confidences = [line.confidence for line in lines if line.confidence is not None]
    found = label_recovery(text)
    return {
        "scale": scale,
        "dpi": int(72 * scale),
        "box_count": len(lines),
        "chars": len("".join(text.split())),
        "mean_conf": round(statistics.fmean(confidences), 4) if confidences else None,
        "min_conf": round(min(confidences), 4) if confidences else None,
        "labels_found": found,
        "labels_found_count": sum(found.values()),
        "labels_missing": [k for k, v in found.items() if not v],
        "ocr_ms": round(elapsed, 1),
        "text": text,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--scales", default="2,3,4")
    parser.add_argument("--show-text", action="store_true")
    args = parser.parse_args()

    scales = [float(s) for s in args.scales.split(",")]
    render_dir = WORK_DIR / "rendered"
    results = []
    for scale in scales:
        image = render(args.path, scale, render_dir)
        result = await measure(image, scale)
        if not args.show_text:
            result.pop("text")
        results.append(result)
        print(
            f"scale={scale} ({result['dpi']} dpi)  boxes={result['box_count']:3d}  "
            f"labels={result['labels_found_count']}/{len(REQUIRED_LABELS)}  "
            f"missing={result['labels_missing']}  "
            f"conf_mean={result['mean_conf']}  {result['ocr_ms']:.0f}ms"
        )

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    (WORK_DIR / "dpi_ablation.json").write_text(
        json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(main())
