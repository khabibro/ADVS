"""Field-value snapshots of the fictional corpora for the checklist impact preview.

One command, no OCR: the harness replays the frozen OCR caches (run from the repo root):

    apps/api/.venv312/bin/python scripts/make_field_snapshot.py

writes evaluation/snapshots/fictional/{dev,holdout,holdout2}.json. Values only: per submission the
document types and, per field, the value and whether the evidence was sufficient. No images, no OCR
text, no file names. holdout3 is final-judgement data and is never touched here.

``--raw FILE --corpus NAME`` converts an existing harness run instead of running one.
``--kind private --raw FILE --corpus NAME`` writes a snapshot of real documents, only to
data/private_real/snapshots/ (git-ignored); labels there are bare case ids.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "apps" / "api"))

from app.checklists.snapshots import (  # noqa: E402
    FICTIONAL_DIR,
    PRIVATE_DIR,
    SCHEMA_ID,
    parse_snapshot,
)
from app.core.domain import DocumentType  # noqa: E402

EVAL = REPO / "evaluation"
CORPORA = {
    "dev": ("phase_d/ocr_cache", "개발 말뭉치"),
    "holdout": ("phase_d/ocr_cache_holdout", "보류 말뭉치 1"),
    "holdout2": ("phase_d2/ocr_cache_holdout2", "보류 말뭉치 2"),
}
WORKFLOW_OF_SET = {"B": "business", "S": "student"}
VALID_TYPES = {t.value for t in DocumentType}


def convert(raw: dict, corpus: str, kind: str, title_ko: str) -> dict:
    when = raw["manifest_submission_date"]
    cases = []
    for set_id, item in sorted(raw["sets"].items()):
        workflow = WORKFLOW_OF_SET.get(set_id[:1])
        if workflow is None:
            continue
        for version, submission in sorted(item["versions"].items()):
            documents = []
            seen: set[str] = set()  # the same file uploaded twice counts once, as in the check
            for record in submission.get("files", []):
                digest = record.get("sha256")
                if digest in seen:
                    continue
                seen.add(digest)
                dtype = record.get("predicted_document_type")
                if record.get("processing_status") != "COMPLETED" or dtype not in VALID_TYPES:
                    continue
                fields = {
                    name: {"value": info.get("value"), "state": info.get("evidence_state")}
                    for name, info in sorted((record.get("fields") or {}).items())
                    if info.get("evidence_state")
                    in {"SUFFICIENT", "REVIEW_REQUIRED", "UNAVAILABLE"}
                }
                documents.append({"type": dtype, "fields": fields})
            if not documents:
                continue
            label = f"{set_id} {version}"
            if kind == "fictional" and item.get("title"):
                label = f"{set_id} {item['title']} ({version})"
            cases.append(
                {
                    "id": f"{set_id}-{version}",
                    "label": label,
                    "workflow": workflow,
                    "check_date": when,
                    "observed_status": submission.get("actual_submission_status"),
                    "documents": documents,
                }
            )
    return {
        "schema": SCHEMA_ID,
        "kind": kind,
        "corpus": corpus,
        "title_ko": title_ko,
        "created": date.today().isoformat(),
        "cases": cases,
    }


def write(snapshot: dict, kind: str, name: str) -> Path:
    parse_snapshot(snapshot)  # strict: values only
    folder = FICTIONAL_DIR if kind == "fictional" else PRIVATE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def replay(corpus: str, cache: Path, out: Path) -> None:
    api = REPO / "apps" / "api"
    env = {**os.environ, "ADVS_MANIFEST_FILE": "manifest_v3.json", "PYTHONPATH": str(api)}
    subprocess.run(
        [
            sys.executable,
            str(EVAL / "harness" / "run_variants.py"),
            "--corpus", corpus,
            "--output", str(out),
            "--ocr-cache", str(cache),
            "--ocr-mode", "replay",
            "--label", f"snapshot_{corpus}",
        ],
        cwd=api,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--raw", type=Path, help="convert this harness run instead of replaying")
    parser.add_argument("--corpus", choices=sorted(CORPORA), help="with --raw")
    parser.add_argument("--kind", choices=["fictional", "private"], default="fictional")
    parser.add_argument("--name", help="file name without .json (default: the corpus)")
    parser.add_argument("--title", help="Korean title shown in the preview")
    parser.add_argument("--evaluation-root", type=Path, default=EVAL, help="where the OCR caches are")
    args = parser.parse_args()

    if args.raw:
        if not args.corpus and args.kind == "fictional":
            parser.error("--raw needs --corpus")
        raw = json.loads(args.raw.read_text(encoding="utf-8"))
        corpus = args.corpus or args.name or "private"
        title = args.title or CORPORA.get(corpus, ("", corpus))[1]
        path = write(convert(raw, corpus, args.kind, title), args.kind, args.name or corpus)
        print(f"wrote {path}")
        return 0
    if args.kind != "fictional":
        parser.error("a private snapshot is made from an existing run: use --raw")
    for corpus, (cache, title) in CORPORA.items():
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "raw.json"
            replay(corpus, args.evaluation_root / cache, out)
            raw = json.loads(out.read_text(encoding="utf-8"))
        print(f"wrote {write(convert(raw, corpus, 'fictional', title), 'fictional', corpus)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
