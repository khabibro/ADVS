#!/bin/sh
cd "$(dirname "$0")/.."
for c in test_variants holdout holdout2; do
  .venv/bin/python scripts/vlm_pages.py --manifest /Users/admin/Documents/ADVS/evaluation/datasets/synthetic/$c/manifest.json --root /Users/admin/Documents/ADVS/evaluation/datasets/synthetic/$c --out results/pages_$c
done
