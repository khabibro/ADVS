#!/bin/sh
# Phase G: full development-data evaluation of the checked-out code, OCR replayed from caches.
# Usage (repo root):  evaluation/phase_g/scripts/dev_gates.sh <label> <main-checkout-evaluation-dir> <out-dir>
# Corpora: test_variants (dev), hold-out 1, hold-out 2 (all development data). Never touches hold-out 3.
set -eu
LABEL=$1; DATA=$2; OUT=$3
API="$(cd apps/api && pwd)"
PY="$DATA/../apps/api/.venv312/bin/python"
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd); DATA=$(cd "$DATA" && pwd)
cd apps/api
for pair in "dev:$DATA/phase_d/ocr_cache" "holdout:$DATA/phase_d/ocr_cache_holdout" "holdout2:$DATA/phase_d2/ocr_cache_holdout2"; do
  c=${pair%%:*}; cache=${pair#*:}
  PYTHONPATH=. $PY ../../evaluation/harness/run_variants.py --corpus $c --output "$OUT/${LABEL}_${c}_raw.json" \
    --ocr-cache "$cache" --ocr-mode replay --label "${LABEL}_${c}" >/dev/null 2>"$OUT/${LABEL}_${c}.err"
  PYTHONPATH=. $PY ../../evaluation/harness/score_d2.py --raw "$OUT/${LABEL}_${c}_raw.json" --corpus $c \
    --out-json "$OUT/${LABEL}_${c}.json" --out-md "$OUT/${LABEL}_${c}_report.md" --label "${LABEL}_${c}"
  PYTHONPATH=. $PY ../../evaluation/harness/inject_errors_d3.py --corpus $c --ocr-cache "$cache" \
    --out "$OUT/${LABEL}_inj_${c}" --label "${LABEL}_${c}" >/dev/null 2>>"$OUT/${LABEL}_${c}.err" || echo "injection step failed for $c"
done
echo done
