#!/bin/sh
# Phase G, step 3: the single final judgement on hold-out set 3. Run once, after every gate on development data passed.
# Baseline = main (95ef2da + Phase F docs); candidate = phase-g/integrated; VLM comparison with the frozen configuration.
# OCR for scans and photos is replayed from the cache recorded on 2026-10-06 (OCR output does not depend on the code under test).
set -eu
export ADVS_FINAL_JUDGEMENT=1
EV=/Users/admin/Documents/ADVS/evaluation
PY=/Users/admin/Documents/ADVS/apps/api/.venv312/bin/python
OUT=/Users/admin/Documents/ADVS-gint/evaluation/phase_g/final
VLM=/Users/admin/Documents/ADVS-vlm/research/vlm_poc
CACHE=$EV/phase_d3/ocr_cache_holdout3
mkdir -p "$OUT"
echo "frozen VLM config: $(python3 -c "import json;print(json.load(open('$VLM/results/frozen.json'))['combined_sha256'])")" | tee "$OUT/session.log"
echo "candidate commit: $(git -C /Users/admin/Documents/ADVS-gint rev-parse HEAD)  baseline app commit: $(git -C /Users/admin/Documents/ADVS-gbase rev-parse HEAD)" | tee -a "$OUT/session.log"
# 1. baseline: main's application code (95ef2da) run by the integrated harness (main's own harness has no hold-out 3 option;
#    on development data this combination reproduces main's recorded numbers exactly)
cd /Users/admin/Documents/ADVS-gbase/apps/api
PYTHONPATH=. $PY ../../evaluation/harness/run_variants.py --corpus holdout3 --output "$OUT/H3_main_raw.json" --ocr-cache "$CACHE" --ocr-mode replay --label H3_main >/dev/null 2>"$OUT/H3_main.err"
PYTHONPATH=. $PY ../../evaluation/harness/score_d2.py --raw "$OUT/H3_main_raw.json" --corpus holdout3 --out-json "$OUT/H3_main.json" --out-md "$OUT/H3_main_report.md" --label H3_main | tee -a "$OUT/session.log"
# 2. candidate (phase-g/integrated)
cd /Users/admin/Documents/ADVS-gint/apps/api
PYTHONPATH=. $PY ../../evaluation/harness/run_variants.py --corpus holdout3 --output "$OUT/H3_integrated_raw.json" --ocr-cache "$CACHE" --ocr-mode replay --label H3_integrated >/dev/null 2>"$OUT/H3_integrated.err"
PYTHONPATH=. $PY ../../evaluation/harness/score_d2.py --raw "$OUT/H3_integrated_raw.json" --corpus holdout3 --out-json "$OUT/H3_integrated.json" --out-md "$OUT/H3_integrated_report.md" --label H3_integrated | tee -a "$OUT/session.log"
PYTHONPATH=. $PY ../../evaluation/harness/inject_errors_d3.py --corpus holdout3 --ocr-cache "$CACHE" --out "$OUT/H3_integrated_inj" --label H3_integrated >/dev/null 2>>"$OUT/H3_integrated.err"
# 3. VLM comparison, same files, frozen configuration
cd "$VLM"
SYN=$EV/datasets/synthetic
.venv/bin/python scripts/vlm_pages.py --manifest $SYN/holdout3/manifest.json --root $SYN/holdout3 --out results/pages_holdout3 >/dev/null 2>results/pages_holdout3.err
PYTHONPATH=/Users/admin/Documents/ADVS-gint/apps/api $PY analysis/compare_fields.py --corpus holdout3 --synth $SYN --harness /Users/admin/Documents/ADVS-gint/evaluation/harness --a-cache "$CACHE" --pages results/pages_holdout3 --scored "$OUT/H3_integrated.json" --out results/fields_holdout3.json | tee -a "$OUT/session.log"
PYTHONPATH=/Users/admin/Documents/ADVS-gint/apps/api $PY analysis/plan_crops.py --corpus holdout3 --synth $SYN --harness /Users/admin/Documents/ADVS-gint/evaluation/harness --a-cache "$CACHE" --fields results/fields_holdout3.json --out results/crops_holdout3 | tee -a "$OUT/session.log"
.venv/bin/python scripts/vlm_crops.py --crops results/crops_holdout3 --out results/crop_readings_holdout3.json | tee -a "$OUT/session.log"
PYTHONPATH=/Users/admin/Documents/ADVS-gint/apps/api $PY analysis/report.py --label "hold-out 3 (final judgement, once)" --harness /Users/admin/Documents/ADVS-gint/evaluation/harness --fields results/fields_holdout3.json --crops results/crops_holdout3 --readings results/crop_readings_holdout3.json --inj "$OUT/H3_integrated_inj.json" --pages results/pages_holdout3 --out results/tables_holdout3.md >/dev/null 2>&1
echo SESSION_DONE | tee -a "$OUT/session.log"
