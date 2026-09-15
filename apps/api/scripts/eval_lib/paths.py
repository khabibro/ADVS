"""Shared path resolution for the evaluation toolkit.

Scripts live at apps/api/scripts/*.py; the `evaluation/` directory lives at
the repository root so it is a single, obvious location regardless of which
app/package touches it later (e.g. a future admin UI).
"""

from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
EVAL_ROOT = REPO_ROOT / "evaluation"

DATASETS_SYNTHETIC = EVAL_ROOT / "datasets" / "synthetic"
DATASETS_RECREATED = EVAL_ROOT / "datasets" / "recreated"
DATASETS_REAL = EVAL_ROOT / "datasets" / "real"
DATASETS_REAL_INBOX = DATASETS_REAL / "inbox"
GOLD_SYNTHETIC = EVAL_ROOT / "gold" / "synthetic"
GOLD_RECREATED = EVAL_ROOT / "gold" / "recreated"
GOLD_REAL = EVAL_ROOT / "gold" / "real"
SUBMISSIONS_DIR = EVAL_ROOT / "submissions"
GOLD_SUBMISSIONS = EVAL_ROOT / "gold" / "submissions"
SOURCES_DIR = EVAL_ROOT / "sources"
RESULTS_DIR = EVAL_ROOT / "results"
REPORTS_DIR = EVAL_ROOT / "reports"
CACHE_DIR = EVAL_ROOT / "cache"
MANIFEST_PATH = EVAL_ROOT / "manifest.json"
SUBMISSIONS_MANIFEST_PATH = EVAL_ROOT / "submissions_manifest.json"
