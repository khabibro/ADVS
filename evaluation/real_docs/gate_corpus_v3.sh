#!/bin/sh
# One fictional corpus, run once with the v3 manifest (OCR replayed from the frozen caches) and scored under BOTH
# scorer v2 (manifest.json; S11 removed from the dev raw run) and scorer v3 (manifest_v3.json), plus the injection
# suites E1-E18 (v2 manifests: S11 is not part of the injection suites).
# Usage (repo root): evaluation/real_docs/gate_corpus_v3.sh <label> <dev|holdout|holdout2|holdout3> <out-dir>
set -eu
LABEL=$1; C=$2; OUT=$3
EV="$(pwd)/evaluation"; PY="$(pwd)/apps/api/.venv312/bin/python"
case $C in dev) CACHE=$EV/phase_d/ocr_cache;; holdout) CACHE=$EV/phase_d/ocr_cache_holdout;; holdout2) CACHE=$EV/phase_d2/ocr_cache_holdout2;; holdout3) CACHE=$EV/phase_d3/ocr_cache_holdout3; export ADVS_FINAL_JUDGEMENT=1;; *) echo "bad corpus"; exit 2;; esac
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
cd apps/api
ADVS_MANIFEST_FILE=manifest_v3.json PYTHONPATH=. $PY ../../evaluation/harness/run_variants.py --corpus $C --output "$OUT/${LABEL}_${C}_raw.json" --ocr-cache "$CACHE" --ocr-mode replay --label "${LABEL}_${C}" >/dev/null 2>"$OUT/${LABEL}_${C}.err"
# scorer v3
PYTHONPATH=. $PY ../../evaluation/harness/score_d3_v3.py --raw "$OUT/${LABEL}_${C}_raw.json" --corpus $C --out-json "$OUT/${LABEL}_${C}.v3.json" --out-md "$OUT/${LABEL}_${C}.v3_report.md" --label "${LABEL}_${C}_v3"
# scorer v2: the same raw run without the v3-only set
$PY - "$OUT/${LABEL}_${C}_raw.json" "$OUT/${LABEL}_${C}_raw_v2view.json" <<'PYEOF'
import json, sys
raw = json.load(open(sys.argv[1]))
raw["sets"].pop("S11", None)
json.dump(raw, open(sys.argv[2], "w"), ensure_ascii=False)
PYEOF
PYTHONPATH=. $PY ../../evaluation/harness/score_d2.py --raw "$OUT/${LABEL}_${C}_raw_v2view.json" --corpus $C --out-json "$OUT/${LABEL}_${C}.v2.json" --out-md "$OUT/${LABEL}_${C}.v2_report.md" --label "${LABEL}_${C}_v2"
PYTHONPATH=. $PY ../../evaluation/harness/inject_errors_d3.py --corpus $C --ocr-cache "$CACHE" --out "$OUT/${LABEL}_inj_${C}" --label "${LABEL}_${C}" >/dev/null 2>>"$OUT/${LABEL}_${C}.err" || echo "injection step failed for $C"
echo "done $C"
