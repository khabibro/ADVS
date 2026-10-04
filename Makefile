API_VENV ?= .venv312
API_BIN = $(API_VENV)/bin

.PHONY: dev dev-api dev-web dev-admin lint typecheck test build format migrate migration-check seed api-lint api-typecheck api-test env-validate security-audit check check-all docker-build docker-check docker-up docker-down eval-variants

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
# Fictional test-variant evaluation.
# ---------------------------------------------------------------------------

eval-variants:
	cd apps/api && $(API_BIN)/python ../../evaluation/phase_b/run_variants.py \
		--output ../../evaluation/phase_b/test_variants_digital.json \
		--versions digital --skip-ocr
