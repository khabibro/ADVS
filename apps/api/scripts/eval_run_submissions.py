"""Runs the submission-bundle (project-level, cross-document) evaluation.

Requires evaluation/manifest.json to already contain the dedicated
`subdoc_*` fixtures -- run `eval_generate.py` first.

Usage:
    cd apps/api && .venv/bin/python scripts/eval_run_submissions.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_lib import paths
from eval_lib.runner import run_submissions


def main() -> None:
    payload = run_submissions()
    paths.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESULTS_DIR / "submissions_latest.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = payload["summary"]
    print(f"Submission bundles: {summary['total']}, correct: {summary['correct']} ({summary['accuracy']:.2%})")
    for bundle in payload["bundles"]:
        mark = "OK" if bundle["correct"] else "MISMATCH"
        print(f"  [{mark}] {bundle['bundle_id']}: expected={bundle['expected_status']} predicted={bundle['predicted_status']}")
    print(f"Results written to {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
