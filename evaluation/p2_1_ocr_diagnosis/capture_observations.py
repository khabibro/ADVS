"""P2.1 raw OCR observation capture.

Runs the *production* PaddleOCR provider entry point unchanged and dumps the
normalized OCR observations with their geometry, confidence and provenance.
Also materializes the exact image the detector saw, so observation-level
ground truth can be annotated in the identical coordinate space.

No production module is modified. Nothing here changes OCR behaviour: it calls
`PaddleOCRProvider.extract_document`, which is what the processing service
calls. Output is written only to the ignored runtime directory.

Usage:
    ADVS_P21_DATASET=~/Desktop/Samples python capture_observations.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path("apps/api").resolve()))

from app.core.config import Settings
from app.document_intelligence.ocr.providers import PaddleOCRProvider

RUNTIME = Path("evaluation/private_runtime/p2_1")
PAGES_DIR = RUNTIME / "pages"
FINGERPRINTS = Path("evaluation/backend_round2/work/p2_original_fingerprints.json")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
PDF_SUFFIXES = {".pdf"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frozen_ids() -> dict[str, str]:
    payload = json.loads(FINGERPRINTS.read_text(encoding="utf-8"))
    return {row["sha256"]: row["sample_id"] for row in payload["records"]}


def materialize_input_images(
    provider: PaddleOCRProvider, path: Path, mime: str, sample: str
) -> list[dict]:
    """Copy out the exact per-page images the detector receives.

    Rendering is deterministic, so these bytes are identical to what
    `extract_document` produces on its own pass; this pass exists only so the
    annotation surface can be saved to disk.
    """
    saved: list[dict] = []
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for page_number, image_path, transform in provider._input_images(path, mime):
        target = PAGES_DIR / f"{sample}_p{page_number}.png"
        shutil.copyfile(image_path, target)
        saved.append(
            {
                "page_number": page_number,
                "image_path": str(target),
                "transform": transform,
            }
        )
    return saved


async def capture() -> int:
    root = Path(os.environ.get("ADVS_P21_DATASET", "~/Desktop/Samples")).expanduser()
    if not root.is_dir():
        print(f"dataset root not found: {root}", file=sys.stderr)
        return 2

    known = frozen_ids()
    files = sorted(
        (
            p
            for p in root.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES | PDF_SUFFIXES
        ),
        key=lambda p: p.name,
    )

    settings = Settings()
    provider = PaddleOCRProvider(settings)

    documents: list[dict] = []
    for path in files:
        digest = sha256_file(path)
        sample = known.get(digest) or f"UNMATCHED-{digest[:8]}"
        mime = "application/pdf" if path.suffix.lower() in PDF_SUFFIXES else None
        if mime is None:
            from PIL import Image

            with Image.open(path) as image:
                mime = Image.MIME.get(
                    image.format or "", f"image/{path.suffix.lstrip('.').lower()}"
                )

        print(f"[{sample}] materializing input images...", flush=True)
        images = materialize_input_images(provider, path, mime, sample)

        print(f"[{sample}] running production OCR...", flush=True)
        pages = await provider.extract_document(path, mime)

        page_records = []
        for page in pages:
            lines = []
            for line in page.lines:
                box = line.bounding_box
                lines.append(
                    {
                        "text": line.text,
                        "confidence": line.confidence,
                        "detection_confidence": line.detection_confidence,
                        "bbox": None
                        if box is None
                        else {
                            "x": box.x,
                            "y": box.y,
                            "width": box.width,
                            "height": box.height,
                        },
                        "polygon": None
                        if line.polygon is None
                        else [list(point) for point in line.polygon],
                        "orientation_degrees": line.orientation_degrees,
                    }
                )
            page_records.append(
                {
                    "page_number": page.page_number,
                    "text": page.text,
                    "page_confidence": page.confidence,
                    "duration_ms": page.duration_ms,
                    "metadata": page.metadata,
                    "line_count": len(page.lines),
                    "lines": lines,
                }
            )

        documents.append(
            {
                "sample_id": sample,
                "sha256": digest,
                "extension": path.suffix.lower().lstrip("."),
                "mime_type": mime,
                "pages": page_records,
                "captured_input_images": images,
            }
        )
        observed = sum(record["line_count"] for record in page_records)
        print(
            f"[{sample}] {len(page_records)} page(s), {observed} observations",
            flush=True,
        )

    RUNTIME.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "p2-1-private-ocr-observations-v1",
        "warning": "CONTAINS OCR TEXT DERIVED FROM PRIVATE DOCUMENTS. Local only; directory is gitignored.",
        "capture_path": "app.document_intelligence.ocr.providers.PaddleOCRProvider.extract_document",
        "production_code_modified": False,
        "environment": {
            "paddleocr": version("paddleocr"),
            "paddlepaddle": version("paddlepaddle"),
            "python": sys.version.split()[0],
            "device": settings.paddle_ocr_device,
            "lang": settings.paddle_ocr_lang,
            "det_model_name": settings.paddle_ocr_det_model_name,
            "rec_model_name": settings.paddle_ocr_rec_model_name,
            "render_dpi": settings.paddle_ocr_render_dpi,
            "doc_orientation": settings.paddle_ocr_doc_orientation,
            "ocr_timeout_seconds": settings.ocr_timeout_seconds,
        },
        "documents": documents,
    }
    (RUNTIME / "observations_private.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = {
        "schema_version": "p2-1-sanitized-observation-summary-v1",
        "environment": payload["environment"],
        "documents": [
            {
                "sample_id": doc["sample_id"],
                "extension": doc["extension"],
                "pages": len(doc["pages"]),
                "observations": sum(p["line_count"] for p in doc["pages"]),
                "observations_without_bbox": sum(
                    1
                    for p in doc["pages"]
                    for line in p["lines"]
                    if line["bbox"] is None
                ),
                "total_ocr_chars": sum(len(p["text"]) for p in doc["pages"]),
                "coordinate_space": sorted(
                    {
                        p["metadata"].get("coordinate_space")
                        for p in doc["pages"]
                        if p.get("metadata")
                    }
                ),
                "transform": [img["transform"] for img in doc["captured_input_images"]],
            }
            for doc in documents
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(capture()))
