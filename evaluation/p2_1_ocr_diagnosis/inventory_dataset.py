"""P2.1 dataset inventory.

Read-only inventory of the private real-document corpus. Emits a sanitized
manifest (safe IDs only) to stdout and a private full record to the ignored
runtime directory. No private filename, path, or text value is written to the
sanitized manifest.

Usage:
    ADVS_P21_DATASET=~/Desktop/Samples python inventory_dataset.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

RUNTIME = Path("evaluation/private_runtime/p2_1")
FINGERPRINTS = Path("evaluation/backend_round2/work/p2_original_fingerprints.json")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif"}
PDF_SUFFIXES = {".pdf"}


@dataclass
class Record:
    sample_id: str
    extension: str
    size_bytes: int
    sha256: str
    page_count: int
    mime_type: str
    embedded_text_chars: int
    image_width: int | None
    image_height: int | None
    orientation: str
    document_category: str
    provenance_category: str
    private_name_sha256: str
    notes: list[str] = field(default_factory=list)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frozen_ids() -> dict[str, str]:
    """sha256 -> safe sample id, from the frozen P1/P2 fingerprint record."""
    if not FINGERPRINTS.exists():
        return {}
    payload = json.loads(FINGERPRINTS.read_text(encoding="utf-8"))
    return {row["sha256"]: row["sample_id"] for row in payload["records"]}


def orientation_of(width: int, height: int) -> str:
    if width == height:
        return "square"
    return "landscape" if width > height else "portrait"


def probe_image(path: Path) -> tuple[int, int, str, list[str]]:
    notes: list[str] = []
    with Image.open(path) as img:
        raw_size = img.size
        fmt = img.format or path.suffix.lstrip(".").upper()
        fixed = ImageOps.exif_transpose(img)
        if fixed.size != raw_size:
            notes.append("exif_orientation_applied")
        exif_orientation = img.getexif().get(0x0112)
        if exif_orientation:
            notes.append(f"exif_orientation_tag={exif_orientation}")
        return fixed.size[0], fixed.size[1], fmt, notes


def probe_pdf(path: Path) -> tuple[int, int, int, list[str]]:
    notes: list[str] = []
    document = pymupdf.open(path)
    try:
        pages = document.page_count
        chars = 0
        width = height = 0
        for index in range(pages):
            page = document.load_page(index)
            chars += len(page.get_text("text") or "")
            rect = page.rect
            width, height = round(rect.width), round(rect.height)
        if chars == 0:
            notes.append("no_embedded_text_layer")
        return pages, chars, (width, height), notes
    finally:
        document.close()


def main() -> int:
    root = Path(os.environ.get("ADVS_P21_DATASET", "~/Desktop/Samples")).expanduser()
    if not root.is_dir():
        print(f"dataset root not found: {root}", file=sys.stderr)
        return 2

    known = frozen_ids()
    candidates = sorted(
        (
            p
            for p in root.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES | PDF_SUFFIXES
        ),
        key=lambda p: p.name,
    )

    records: list[Record] = []
    anonymous: list[Record] = []
    for path in candidates:
        digest = sha256_file(path)
        safe_id = known.get(digest)
        suffix = path.suffix.lower()
        if suffix in PDF_SUFFIXES:
            pages, chars, (width, height), notes = probe_pdf(path)
            mime = "application/pdf"
            if width and height:
                notes.append(f"pdf_page_pt={width}x{height}")
        else:
            width, height, fmt, notes = probe_image(path)
            pages = 1
            chars = 0
            mime = Image.MIME.get(fmt, f"image/{fmt.lower()}")
            notes.append("raster_no_embedded_text_layer")
        record = Record(
            sample_id=safe_id or f"UNMATCHED-{digest[:8]}",
            extension=suffix.lstrip("."),
            size_bytes=path.stat().st_size,
            sha256=digest,
            page_count=pages,
            mime_type=mime,
            embedded_text_chars=chars,
            image_width=width,
            image_height=height,
            orientation=orientation_of(width, height),
            document_category="PENDING_SAFE_DETERMINATION",
            provenance_category="PENDING_SAFE_DETERMINATION",
            private_name_sha256=hashlib.sha256(path.name.encode()).hexdigest(),
            notes=notes,
        )
        records.append(record)
        anonymous.append(record)

    RUNTIME.mkdir(parents=True, exist_ok=True)
    private_payload = {
        "schema_version": "p2-1-private-dataset-inventory-v1",
        "dataset_root_recorded": False,
        "records": [asdict(r) for r in records],
    }
    (RUNTIME / "dataset_inventory_private.json").write_text(
        json.dumps(private_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sanitized = {
        "schema_version": "p2-1-sanitized-dataset-inventory-v1",
        "documents": len(records),
        "unique_hashes": len({r.sha256 for r in records}),
        "matched_to_frozen_ids": sum(
            1 for r in records if not r.sample_id.startswith("UNMATCHED")
        ),
        "records": [
            {k: v for k, v in asdict(r).items() if k not in {"private_name_sha256"}}
            for r in records
        ],
        "private_filenames_recorded": False,
    }
    print(json.dumps(sanitized, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
