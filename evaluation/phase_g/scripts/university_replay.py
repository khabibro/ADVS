"""Phase G / G-2: replay cached OCR through the current extractors and score `university_name`.

Development data only (test_variants, hold-out 1, hold-out 2). It reads the OCR text cached by
earlier runs, so no OCR runs. Ground truth comes from the scored Phase D2 files. Hold-out set 3
is not referenced anywhere.

  cd apps/api && PYTHONPATH=. .venv312/bin/python ../../evaluation/phase_g/scripts/university_replay.py \
      [--data-root /path/to/main/checkout/evaluation]
"""

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

CORPORA = [
    ("test_variants", "phase_d2/B2_D2_dev.json", "datasets/synthetic/test_variants/", "phase_d/ocr_cache"),
    ("hold-out 1", "phase_d2/B2_D2_holdout.json", "datasets/synthetic/holdout/", "phase_d/ocr_cache_holdout"),
    ("hold-out 2", "phase_d2/H2_B1.json", "datasets/synthetic/holdout2/", "phase_d2/ocr_cache_holdout2"),
]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (centre - half, centre + half)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root: Path = args.data_root
    sys.path.insert(0, str(root / "harness"))
    from harness_core import page_from_dict  # type: ignore[import-not-found]

    from app.core.domain import DocumentType
    from app.document_intelligence.extraction.registry import ExtractorRegistry
    from app.document_intelligence.ocr.models import OCRDocumentResult
    from app.document_intelligence.ocr.text_assembly import assemble_document_text, assemble_page_text

    registry = ExtractorRegistry()
    tally: dict[tuple[str, str], collections.Counter] = collections.defaultdict(collections.Counter)
    failures: list[dict] = []
    for corpus, scored, data, cache in CORPORA:
        result = json.loads((root / scored).read_text(encoding="utf-8"))
        for _set_id, entry in result["scored"]["sets"].items():
            for version, block in entry["versions"].items():
                if version == "digital":
                    continue
                for item in block["files"]:
                    truth = (item.get("fields") or {}).get("university_name")
                    if not truth or not truth.get("expected"):
                        continue
                    digest = hashlib.sha256((root / data / item["file"]).read_bytes()).hexdigest()
                    cached = json.loads((root / cache / f"{digest}.json").read_text(encoding="utf-8"))
                    pages = [page_from_dict(page) for page in cached["pages"]]
                    for page in pages:
                        page.metadata.setdefault("source", "ocr")
                        if page.lines:
                            page.text = assemble_page_text(page.lines)
                    source = OCRDocumentResult("replay", pages, assemble_document_text(pages))
                    values = registry.extract(DocumentType(item["expected"]), source)
                    got = next((v.normalized_value for v in values if v.field_name == "university_name"), None)
                    outcome = "correct" if got == truth["expected"] else ("missing" if got is None else "wrong")
                    tally[(corpus, version)][outcome] += 1
                    tally[("all", version)][outcome] += 1
                    if outcome != "correct":
                        failures.append({"corpus": corpus, "file": item["file"], "expected": truth["expected"], "got": got})
    report = {}
    for (corpus, version), counts in sorted(tally.items()):
        n = sum(counts.values())
        low, high = wilson(counts["correct"], n)
        report[f"{corpus} / {version}"] = {**counts, "n": n, "exact": f"{counts['correct']}/{n}", "wilson95": [round(low, 3), round(high, 3)]}
        print(f"{corpus:14s} {version:8s} correct {counts['correct']:3d}/{n:3d}  wrong {counts['wrong']:2d}  missing {counts['missing']:3d}  Wilson95 [{low:.2f}, {high:.2f}]")
    if args.json:
        print(json.dumps({"report": report, "failures": failures}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
