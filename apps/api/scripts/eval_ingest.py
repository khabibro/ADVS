"""Ingests files dropped into evaluation/datasets/real/inbox/.

For each new file this:
  1. validates it is a supported, non-corrupt PDF/PNG/JPEG,
  2. assigns a safe sequential sample ID (real_0001, ...),
  3. copies it into evaluation/datasets/real/unlabeled/<sample_id>.<ext>,
  4. writes an UNVERIFIED gold-label template to evaluation/gold/real/,
  5. registers it in evaluation/manifest.json with source="real",
  6. leaves the original file in the inbox untouched (so re-running is safe;
     already-ingested files are skipped by content hash).

It never assigns a document_type or field values -- that is exactly the
human labeling step `eval_label.py` exists for. See
evaluation/datasets/real/README.md for the full policy.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_lib import paths
from eval_lib.schema import GoldLabel, Manifest, ManifestEntry

try:
    import fitz
    from PIL import Image, UnidentifiedImageError
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"Missing dependency: {exc}") from None

_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


def _validate(path: Path) -> str | None:
    """Returns an error string, or None if the file is acceptable."""
    ext = path.suffix.lower()
    if ext not in _SIGNATURES:
        return f"unsupported extension {ext}"
    header = path.read_bytes()[:8]
    if not any(header.startswith(sig) for sig in _SIGNATURES[ext]):
        return "file content does not match its extension (magic bytes mismatch)"
    try:
        if ext == ".pdf":
            with fitz.open(path):
                pass
        else:
            with Image.open(path) as img:
                img.verify()
    except (RuntimeError, UnidentifiedImageError, OSError) as exc:
        return f"file could not be opened; possibly corrupt ({exc})"
    return None


def _next_sample_index(existing_ids: set[str]) -> int:
    used = [int(sid.split("_")[1]) for sid in existing_ids if sid.startswith("real_")]
    return (max(used) + 1) if used else 1


def main() -> None:
    unlabeled_dir = paths.DATASETS_REAL / "unlabeled"
    unlabeled_dir.mkdir(parents=True, exist_ok=True)
    paths.GOLD_REAL.mkdir(parents=True, exist_ok=True)

    manifest_data: dict = (
        json.loads(paths.MANIFEST_PATH.read_text(encoding="utf-8"))
        if paths.MANIFEST_PATH.exists()
        else {"manifest_version": "1.0", "generator_seed": 42, "entries": []}
    )
    manifest = Manifest(
        manifest_version=manifest_data["manifest_version"],
        generator_seed=manifest_data["generator_seed"],
        entries=[ManifestEntry(**e) for e in manifest_data["entries"]],
    )
    existing_ids = {e.sample_id for e in manifest.entries}
    already_ingested_hashes = set()
    for gold_path in paths.GOLD_REAL.glob("*.json"):
        data = json.loads(gold_path.read_text(encoding="utf-8"))
        already_ingested_hashes.add(data.get("notes", ""))  # notes carries the source hash marker

    inbox_files = sorted(
        p for p in paths.DATASETS_REAL_INBOX.iterdir() if p.is_file() and p.name != ".gitkeep"
    )
    if not inbox_files:
        print(f"No files found in {paths.DATASETS_REAL_INBOX.relative_to(paths.REPO_ROOT)}.")
        return

    ingested = skipped = rejected = 0
    for path in inbox_files:
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        hash_marker = f"source_hash:{content_hash}"
        if hash_marker in already_ingested_hashes:
            skipped += 1
            continue

        error = _validate(path)
        if error:
            print(f"REJECTED {path.name}: {error}")
            rejected += 1
            continue

        index = _next_sample_index(existing_ids)
        sample_id = f"real_{index:04d}"
        existing_ids.add(sample_id)

        dest = unlabeled_dir / f"{sample_id}{path.suffix.lower()}"
        shutil.copy2(path, dest)

        gold = GoldLabel(
            sample_id=sample_id,
            source="real",
            document_type="UNKNOWN",
            input_format=path.suffix.lower().strip("."),
            quality="unknown",
            layout_variant="unknown",
            split="dev",
            fields={},
            expected_validation_status=None,
            notes=hash_marker,
            verified=False,
        )
        gold_path = paths.GOLD_REAL / f"{sample_id}.json"
        gold_path.write_text(
            json.dumps(gold.to_json(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

        manifest.entries.append(
            ManifestEntry(
                sample_id=sample_id,
                source="real",
                document_type="UNKNOWN",
                gold_text_path="",
                rendered_file_path=str(dest.relative_to(paths.REPO_ROOT)),
                gold_label_path=str(gold_path.relative_to(paths.REPO_ROOT)),
                split="dev",
            )
        )
        ingested += 1
        print(f"Ingested {path.name} -> {sample_id} (UNVERIFIED, needs labeling)")

    paths.MANIFEST_PATH.write_text(
        json.dumps(manifest.to_json(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nIngested: {ingested}, already-ingested (skipped): {skipped}, rejected: {rejected}")
    if ingested:
        print("Run `make eval-label` next to assign document types and gold field values.")


if __name__ == "__main__":
    main()
