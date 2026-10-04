"""P1 dataset inventory.

Read-only. Records safe ids, hashes and structural facts only. No values, no
filenames, no personal data in the emitted manifest.

The private directory is discovered, never hardcoded: an explicit
``--private-dir`` wins, then ``ADVS_PRIVATE_DIR``, then a small set of
conventional names under the user's Desktop. Use ``--print-discovery`` to see
what was searched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
P1_DIR = REPO_ROOT / "evaluation" / "p1_layout"

ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

# Conventional locations, tried in order. The samples subfolder first because
# that is where this owner's corpus actually lives.
_DISCOVERY_SUFFIXES = ("samples", "Samples", "SAMPLES", "sample_docs", "documents")


def _norm(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def discover_private_dir(explicit: str | None = None) -> Path | None:
    if explicit:
        candidate = Path(explicit).expanduser()
        return candidate if candidate.is_dir() else None
    env = os.environ.get("ADVS_PRIVATE_DIR")
    if env:
        candidate = Path(env).expanduser()
        return candidate if candidate.is_dir() else None
    desktop = Path.home() / "Desktop"
    if not desktop.is_dir():
        return None
    for name in _DISCOVERY_SUFFIXES:
        candidate = desktop / name
        if candidate.is_dir() and any(
            child.suffix.lower() in ALLOWED_SUFFIXES for child in candidate.iterdir()
        ):
            return candidate
    if any(child.suffix.lower() in ALLOWED_SUFFIXES for child in desktop.iterdir()):
        return desktop
    return None


@dataclass(frozen=True)
class Sample:
    sample_id: str
    path: Path
    suffix: str
    size_bytes: int
    sha256: str


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_mime(path: Path) -> str:
    with path.open("rb") as handle:
        head = handle.read(32)
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def collect(private_dir: Path) -> list[Sample]:
    files = sorted(
        (child for child in private_dir.iterdir() if child.is_file()),
        key=lambda item: _norm(item.name),
    )
    supported = [item for item in files if item.suffix.lower() in ALLOWED_SUFFIXES]
    samples = []
    for index, path in enumerate(supported, start=1):
        samples.append(
            Sample(
                sample_id=f"P1-{index:03d}",
                path=path,
                suffix=path.suffix.lower(),
                size_bytes=path.stat().st_size,
                sha256=sha256_of(path),
            )
        )
    return samples


def structural_facts(sample: Sample) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "sample_id": sample.sample_id,
        "extension": sample.suffix,
        "size_bytes": sample.size_bytes,
        "sha256": sample.sha256,
        "detected_mime": detect_mime(sample.path),
        "pages": 1,
        "embedded_text_chars": 0,
        "input_kind": "image",
        "width": None,
        "height": None,
        "page_points": None,
        "scanned": True,
        "orientation_hint": None,
    }
    if sample.suffix == ".pdf":
        import fitz  # local import: only needed for PDFs

        with fitz.open(sample.path) as document:
            facts["input_kind"] = "pdf"
            facts["pages"] = document.page_count
            facts["encrypted"] = bool(document.needs_pass)
            facts["page_points"] = [
                [round(page.rect.width, 2), round(page.rect.height, 2)] for page in document
            ]
            facts["embedded_text_chars"] = sum(
                len(page.get_text().strip()) for page in document
            )
            facts["scanned"] = facts["embedded_text_chars"] < 20
        facts["width"], facts["height"] = facts["page_points"][0]
    else:
        from PIL import Image

        with Image.open(sample.path) as image:
            facts["width"], facts["height"] = image.size
            facts["pillow_format"] = image.format
            facts["pillow_mode"] = image.mode
            facts["exif_orientation"] = image.getexif().get(274, 1)
    if facts["width"] and facts["height"]:
        facts["orientation_hint"] = (
            "landscape" if facts["width"] > facts["height"] else "portrait"
        )
    return facts


def environment() -> dict[str, Any]:
    info: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
    }
    try:
        import paddle  # noqa: PLC0415

        info["paddlepaddle"] = paddle.__version__
    except Exception:  # noqa: BLE001
        info["paddlepaddle"] = None
    try:
        import paddleocr  # noqa: PLC0415

        info["paddleocr"] = paddleocr.__version__
    except Exception:  # noqa: BLE001
        info["paddleocr"] = None
    try:
        import paddlex  # noqa: PLC0415

        info["paddlex"] = paddlex.__version__
    except Exception:  # noqa: BLE001
        info["paddlex"] = None
    try:
        import fitz  # noqa: PLC0415

        info["pymupdf"] = fitz.__doc__.split()[1] if fitz.__doc__ else "unknown"
    except Exception:  # noqa: BLE001
        info["pymupdf"] = None
    return info


def model_inventory(cache_dir: Path | None) -> list[dict[str, Any]]:
    if cache_dir is None or not cache_dir.is_dir():
        return []
    entries = []
    root = cache_dir / "official_models"
    if not root.is_dir():
        return []
    for model in sorted(root.iterdir()):
        if not model.is_dir():
            continue
        size = sum(f.stat().st_size for f in model.rglob("*") if f.is_file())
        entries.append({"name": model.name, "bytes": size})
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", default=None)
    parser.add_argument("--out", default=str(P1_DIR / "dataset_manifest.json"))
    parser.add_argument(
        "--cache-dir", default=os.environ.get("PADDLE_OCR_CACHE_DIR")
    )
    parser.add_argument("--print-discovery", action="store_true")
    args = parser.parse_args()

    private_dir = discover_private_dir(args.private_dir)
    if private_dir is None:
        print("Could not locate a private document directory.")
        print("Pass --private-dir or set ADVS_PRIVATE_DIR.")
        return 2
    if args.print_discovery:
        print(f"private dir resolved: {private_dir}")

    samples = collect(private_dir)
    records = [structural_facts(sample) for sample in samples]
    cache_dir = Path(args.cache_dir).expanduser() if args.cache_dir else None
    manifest = {
        "schema_version": "p1-dataset-manifest-v1",
        "private_dir_label": "resolved at runtime, never recorded",
        "private_dir_sha256_of_names": hashlib.sha256(
            "\n".join(_norm(s.path.name) for s in samples).encode()
        ).hexdigest(),
        "total_files": len(records),
        "unique_sha256": len({r["sha256"] for r in records}),
        "duplicate_sha256": [],
        "all_scanned": all(r["scanned"] for r in records),
        "page_count_total": sum(r["pages"] for r in records),
        "records": records,
        "environment": environment(),
        "models_cached": model_inventory(cache_dir),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"files={manifest['total_files']} unique_sha256={manifest['unique_sha256']}")
    print(f"all_scanned={manifest['all_scanned']} pages={manifest['page_count_total']}")
    for record in records:
        print(
            f"  {record['sample_id']} {record['extension']:>5} "
            f"{record['pages']}p {record['detected_mime']:<18} "
            f"embedded_text={record['embedded_text_chars']}"
        )
    print(f"environment: {manifest['environment']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())