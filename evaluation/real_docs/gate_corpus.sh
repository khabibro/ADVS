#!/bin/sh
# One corpus of the fictional-set safety gates (OCR replayed from the frozen caches), for the checked-out code.
# Usage (repo root): evaluation/real_docs/gate_corpus.sh <label> <dev|holdout|holdout2> <out-dir>
# hold-out 3 is never run here (final judgement only, see PHASE_G_REPORT / REAL_DOCS_REPORT).
set -eu
LABEL=$1; C=$2; OUT=$3
EV="$(pwd)/evaluation"; PY="$(pwd)/apps/api/.venv312/bin/python"
case $C in dev) CACHE=$EV/phase_d/ocr_cache;; holdout) CACHE=$EV/phase_d/ocr_cache_holdout;; holdout2) CACHE=$EV/phase_d2/ocr_cache_holdout2;; *) echo "bad corpus"; exit 2;; esac
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
cd apps/api
PYTHONPATH=. $PY ../../evaluation/harness/run_variants.py --corpus $C --output "$OUT/${LABEL}_${C}_raw.json" --ocr-cache "$CACHE" --ocr-mode replay --label "${LABEL}_${C}" >/dev/null 2>"$OUT/${LABEL}_${C}.err"
PYTHONPATH=. $PY ../../evaluation/harness/score_d2.py --raw "$OUT/${LABEL}_${C}_raw.json" --corpus $C --out-json "$OUT/${LABEL}_${C}.json" --out-md "$OUT/${LABEL}_${C}_report.md" --label "${LABEL}_${C}"
PYTHONPATH=. $PY ../../evaluation/harness/inject_errors_d3.py --corpus $C --ocr-cache "$CACHE" --out "$OUT/${LABEL}_inj_${C}" --label "${LABEL}_${C}" >/dev/null 2>>"$OUT/${LABEL}_${C}.err" || echo "injection step failed for $C"
echo "done $C"
