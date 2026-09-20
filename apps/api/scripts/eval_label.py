"""Human labeling workflow for real/anonymized evaluation samples.

Lists every unverified real gold label and tells you exactly what to do:
open the file at `evaluation/datasets/real/unlabeled/<sample_id>.<ext>`,
look at it yourself, then edit the matching gold JSON in
evaluation/gold/real/ and fill in `document_type`, each field's `value`,
and `expected_validation_status`, then set `"verified": true`.

This tool deliberately does NOT run the pipeline and copy its prediction
into the gold file -- a prediction is not ground truth (see
evaluation/datasets/real/README.md).

Usage:
    cd apps/api && .venv/bin/python scripts/eval_label.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_lib import paths

from app.core.domain import EXPECTED_FIELDS, DocumentType


def main() -> None:
    if not paths.GOLD_REAL.exists():
        print("No real gold labels directory found -- run eval_ingest.py first.")
        return

    unverified = []
    for gold_path in sorted(paths.GOLD_REAL.glob("*.json")):
        data = json.loads(gold_path.read_text(encoding="utf-8"))
        if not data.get("verified", False):
            unverified.append((gold_path, data))

    if not unverified:
        print("No unverified real samples. (Nothing in evaluation/gold/real/ is pending review.)")
        return

    print(f"{len(unverified)} unverified real sample(s):\n")
    for gold_path, data in unverified:
        sample_id = data["sample_id"]
        matches = list((paths.DATASETS_REAL / "unlabeled").glob(f"{sample_id}.*"))
        source_path = matches[0] if matches else None
        print(f"- {sample_id}")
        print(
            f"    document: {source_path.relative_to(paths.REPO_ROOT) if source_path else '(missing!)'}"
        )
        print(f"    gold label to edit: {gold_path.relative_to(paths.REPO_ROOT)}")
        print("    steps: open the document yourself, then edit the gold label JSON:")
        print('      1. set "document_type" to one of: ' + ", ".join(t.value for t in DocumentType))
        print(
            '      2. fill each field\'s "value" (see app/core/domain.py EXPECTED_FIELDS for the field list'
        )
        print("         per document type -- do not invent new field names)")
        print(
            '      3. set "expected_validation_status" to "READY", '
            '"REVIEW_REQUIRED", or "NEEDS_CORRECTION"'
        )
        print(
            '      4. set "verified": true only once you have confirmed the values against the document'
        )
        print()

    print("Reference -- expected fields per type:")
    for doc_type, fields in EXPECTED_FIELDS.items():
        if fields:
            print(f"  {doc_type}: {', '.join(fields)}")


if __name__ == "__main__":
    main()
