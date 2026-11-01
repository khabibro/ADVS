"""Field / status diff between two harness raw runs (e.g. origin/main vs a branch), replayed from the
same frozen OCR caches.

    python scripts/compare_harness_runs.py BASE_DIR MINE_DIR --corpora dev holdout holdout2

Each directory holds ``<label>_<corpus>_raw.json`` files (evaluation/harness/run_variants.py output);
the label is taken from the file names. Prints the number of submissions and fields compared, the
status and field-value differences (must be 0), and the review items that appeared or disappeared,
by document type and field.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load(folder: Path, corpus: str) -> dict:
    path = max(folder.glob(f"*_{corpus}_raw.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("mine", type=Path)
    parser.add_argument("--corpora", nargs="+", default=["dev", "holdout", "holdout2"])
    args = parser.parse_args()
    submissions = fields = 0
    status_diffs: list[tuple] = []
    value_diffs: list[tuple] = []
    gone: Counter = Counter()
    new: Counter = Counter()
    for corpus in args.corpora:
        a, b = load(args.base, corpus), load(args.mine, corpus)
        for collection in ("sets", "format_sets"):
            for set_id, item in a.get(collection, {}).items():
                for version, left in item.get("versions", {}).items():
                    right = b[collection][set_id]["versions"][version]
                    submissions += 1
                    if left["actual_submission_status"] != right["actual_submission_status"]:
                        status_diffs.append(
                            (corpus, set_id, version, left["actual_submission_status"], right["actual_submission_status"])
                        )
                    right_files = {f["file"]: f for f in right["files"]}
                    for record in left["files"]:
                        other = right_files[record["file"]]
                        for name in set(record.get("fields", {})) | set(other.get("fields", {})):
                            fields += 1
                            x = record.get("fields", {}).get(name) or {}
                            y = other.get("fields", {}).get(name) or {}
                            if (x.get("value"), x.get("evidence_state")) != (y.get("value"), y.get("evidence_state")):
                                value_diffs.append((corpus, set_id, version, record["file"], name))

                    def items(run):
                        kinds = {f["document_id"]: f.get("predicted_document_type") for f in run["files"] if f.get("document_id")}
                        return Counter((kinds[i["document_id"]], i["field_name"]) for i in run["review_items"])

                    gone.update(items(left) - items(right))
                    new.update(items(right) - items(left))
    print(f"submissions compared: {submissions}, fields compared: {fields}")
    print(f"status differences: {len(status_diffs)}   field-value differences: {len(value_diffs)}")
    for row in status_diffs[:20] + value_diffs[:20]:
        print("  ", row)
    print("review items only in BASE:", dict(gone) or "none")
    print("review items only in MINE:", dict(new) or "none")
    return 1 if status_diffs or value_diffs or new else 0


if __name__ == "__main__":
    raise SystemExit(main())
