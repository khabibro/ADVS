API_VENV ?= .venv312
API_BIN = $(API_VENV)/bin

.PHONY: dev dev-api dev-web dev-admin lint typecheck test build format migrate migration-check seed api-lint api-typecheck api-test env-validate security-audit check check-all docker-build docker-check docker-up docker-down eval-generate eval-synthetic eval-held-out eval-paddle eval-report eval-ingest eval-label eval research-sources dataset-recreate dataset-variants eval-recreated eval-public eval-submissions baseline-fast baseline

dev:
	docker compose up --build

dev-api:
	cd apps/api && $(API_BIN)/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	pnpm --filter @advs/web dev

dev-admin:
	pnpm --filter @advs/admin dev

lint:
	$(MAKE) api-lint
	pnpm lint

typecheck:
	$(MAKE) api-typecheck
	pnpm typecheck

test:
	$(MAKE) api-test
	pnpm test

build:
	pnpm build

format:
	cd apps/api && $(API_BIN)/ruff format .
	pnpm --filter @advs/web format
	pnpm --filter @advs/admin format

migrate:
	cd apps/api && $(API_BIN)/alembic upgrade head

migration-check:
	cd apps/api && $(API_BIN)/alembic upgrade head && $(API_BIN)/alembic heads

seed:
	cd apps/api && PYTHONPATH=../..:. $(API_BIN)/python ../../scripts/seed.py

api-lint:
	cd apps/api && $(API_BIN)/ruff check .

api-typecheck:
	cd apps/api && $(API_BIN)/mypy --explicit-package-bases app

api-test:
	cd apps/api && $(API_BIN)/pytest

env-validate:
	pnpm env:validate

security-audit:
	pnpm security:audit

check:
	$(MAKE) env-validate
	$(MAKE) security-audit
	$(MAKE) api-lint
	$(MAKE) api-typecheck
	$(MAKE) api-test
	pnpm lint
	pnpm typecheck
	pnpm test

check-all:
	$(MAKE) check
	pnpm build
	pnpm contracts:generate
	$(MAKE) migration-check
	$(MAKE) docker-check

docker-build:
	docker compose build

docker-check:
	docker compose config

docker-up:
	docker compose up --build

docker-down:
	docker compose down

# ---------------------------------------------------------------------------
# Evaluation toolkit (see evaluation/README.md). OCR evaluation is not wired
# into check/check-all because PaddleOCR model downloads and CPU inference are
# too heavy for the normal quality gate.
# ---------------------------------------------------------------------------

# Regenerates the deterministic synthetic benchmark (seeded, reproducible).
eval-generate:
	cd apps/api && $(API_BIN)/python scripts/eval_generate.py

# Mode A (mock/controlled): scores classification/extraction/validation
# against gold text directly. No OCR provider involved.
eval-synthetic:
	cd apps/api && $(API_BIN)/python scripts/eval_run.py --mode mock --split dev --output dev_latest

eval-held-out:
	cd apps/api && $(API_BIN)/python scripts/eval_run.py --mode mock --split held_out --output held_out_latest

eval-paddle:
	cd apps/api && $(API_BIN)/python scripts/eval_run.py --mode paddle --output paddle_latest

eval-report:
	cd apps/api && $(API_BIN)/python scripts/eval_report.py \
		--dev ../../evaluation/results/dev_latest.json \
		--held-out ../../evaluation/results/held_out_latest.json \
		--output ../../evaluation/reports/latest.md

# Ingests files from evaluation/datasets/real/inbox/ and lists what needs
# human labeling -- see evaluation/datasets/real/README.md.
eval-ingest:
	cd apps/api && $(API_BIN)/python scripts/eval_ingest.py

eval-label:
	cd apps/api && $(API_BIN)/python scripts/eval_label.py

# Full synthetic evaluation cycle: regenerate, run both splits, report.
eval:
	$(MAKE) eval-generate
	$(MAKE) eval-synthetic
	$(MAKE) eval-held-out
	$(MAKE) eval-report

# ---------------------------------------------------------------------------
# Realistic-dataset research & recreation (see evaluation/reports/
# source_research.md, evaluation/sources/source_registry.json).
# ---------------------------------------------------------------------------

# Deep web research is an interactive/manual step (see the research report);
# this target just points at where the results live and how they were used.
research-sources:
	@echo "Source research is documented in:"
	@echo "  evaluation/reports/source_research.md"
	@echo "  evaluation/sources/source_registry.json"
	@echo "No third-party file was downloaded -- every source is RECREATE_ONLY."

# RECREATED_FROM_PUBLIC_REFERENCE samples and layout/format/quality variants
# are produced by the same deterministic generator as the rest of the
# synthetic benchmark -- eval-generate regenerates everything together.
dataset-recreate: eval-generate
dataset-variants: eval-generate

# Scores only RECREATED_FROM_PUBLIC_REFERENCE samples (all splits).
eval-recreated:
	cd apps/api && $(API_BIN)/python scripts/eval_run.py --mode mock --source-class RECREATED_FROM_PUBLIC_REFERENCE --output recreated_latest

# No OFFICIAL_PUBLIC_REFERENCE (actual downloaded public file) samples exist
# by policy -- see evaluation/sources/source_registry.json (every source is
# RECREATE_ONLY). This target says so explicitly rather than silently
# running an empty/misleading evaluation.
eval-public:
	@echo "PUBLIC REFERENCE EVALUATION: NOT APPLICABLE"
	@echo "No third-party file is downloaded/stored (see evaluation/sources/source_registry.json)."
	@echo "Use 'make eval-recreated' for the from-scratch recreations motivated by that research."

# Project-level (cross-document) validation: name/company consistency,
# duplicate detection, missing required documents. Requires eval-generate
# to have already produced the dedicated subdoc_* fixtures.
eval-submissions:
	cd apps/api && $(API_BIN)/python scripts/eval_run_submissions.py

# Phase 0 reproducible baseline snapshots. baseline-fast uses a deterministic
# one-sample-per-document-type subset; baseline runs the full gold-text and
# PaddleOCR benchmark and writes evaluation/baselines/baseline_v0.{json,md}.
baseline-fast: eval-generate
	cd apps/api && $(API_BIN)/python scripts/eval_baseline.py --fast --name baseline_v0_fast

baseline: eval-generate
	cd apps/api && $(API_BIN)/python scripts/eval_baseline.py --name baseline_v0
