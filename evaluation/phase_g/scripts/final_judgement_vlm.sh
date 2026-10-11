#!/bin/sh
# Phase G, step 3 (part 2): the VLM comparison of the single hold-out 3 session. Part 1 (final_judgement.sh) produced the baseline,
# candidate and injection results; its VLM stage stopped because it pointed at main's data folder, which has no manifest.json.
# Same frozen configuration, same files; only the dataset path differs (the integrated worktree holds the manifest).
set -eu
export ADVS_FINAL_JUDGEMENT=1
EV=/Users/admin/Documents/ADVS/evaluation
PY=/Users/admin/Documents/ADVS/apps/api/.venv312/bin/python
OUT=/Users/admin/Documents/ADVS-gint/evaluation/phase_g/final
VLM=/Users/admin/Documents/ADVS-vlm/research/vlm_poc
CACHE=$EV/phase_d3/ocr_cache_holdout3
# 3. VLM comparison, same files, frozen configuration
cd "$VLM"
SYN=/Users/admin/Documents/ADVS-gint/evaluation/datasets/synthetic
.venv/bin/python scripts/vlm_pages.py --manifest $SYN/holdout3/manifest.json --root $SYN/holdout3 --out results/pages_holdout3 >/dev/null 2>results/pages_holdout3.err
PYTHONPATH=/Users/admin/Documents/ADVS-gint/apps/api $PY analysis/compare_fields.py --corpus holdout3 --synth $SYN --harness /Users/admin/Documents/ADVS-gint/evaluation/harness --a-cache "$CACHE" --pages results/pages_holdout3 --scored "$OUT/H3_integrated.json" --out results/fields_holdout3.json | tee -a "$OUT/session.log"
PYTHONPATH=/Users/admin/Documents/ADVS-gint/apps/api $PY analysis/plan_crops.py --corpus holdout3 --synth $SYN --harness /Users/admin/Documents/ADVS-gint/evaluation/harness --a-cache "$CACHE" --fields results/fields_holdout3.json --out results/crops_holdout3 | tee -a "$OUT/session.log"
.venv/bin/python scripts/vlm_crops.py --crops results/crops_holdout3 --out results/crop_readings_holdout3.json | tee -a "$OUT/session.log"
PYTHONPATH=/Users/admin/Documents/ADVS-gint/apps/api $PY analysis/report.py --label "hold-out 3 (final judgement, once)" --harness /Users/admin/Documents/ADVS-gint/evaluation/harness --fields results/fields_holdout3.json --crops results/crops_holdout3 --readings results/crop_readings_holdout3.json --inj "$OUT/H3_integrated_inj.json" --pages results/pages_holdout3 --out results/tables_holdout3.md >/dev/null 2>&1
echo SESSION_DONE | tee -a "$OUT/session.log"
