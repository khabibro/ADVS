#!/bin/sh
# Hold-out 3 REGRESSION CHECK (development data since Phase G; not a test). Same replay as gate_corpus.sh.
# Usage (repo root): evaluation/real_docs/regress_holdout3.sh <label> <out-dir>
set -eu
export ADVS_FINAL_JUDGEMENT=1
LABEL=$1; OUT=$2
EV="$(pwd)/evaluation"; PY="$(pwd)/apps/api/.venv312/bin/python"; CACHE=$EV/phase_d3/ocr_cache_holdout3
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
cd apps/api
PYTHONPATH=. $PY ../../evaluation/harness/run_variants.py --corpus holdout3 --output "$OUT/${LABEL}_h3_raw.json" --ocr-cache "$CACHE" --ocr-mode replay --label "${LABEL}_h3" >/dev/null 2>"$OUT/${LABEL}_h3.err"
PYTHONPATH=. $PY ../../evaluation/harness/score_d2.py --raw "$OUT/${LABEL}_h3_raw.json" --corpus holdout3 --out-json "$OUT/${LABEL}_h3.json" --out-md "$OUT/${LABEL}_h3_report.md" --label "${LABEL}_h3"
PYTHONPATH=. $PY ../../evaluation/harness/inject_errors_d3.py --corpus holdout3 --ocr-cache "$CACHE" --out "$OUT/${LABEL}_inj_h3" --label "${LABEL}_h3" >/dev/null 2>>"$OUT/${LABEL}_h3.err"
echo done
