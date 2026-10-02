# Quality gates

Every command was run on the final P0 tree. Backend commands ran in `apps/api`
against the project virtual environment.

## Backend

| Command | Result |
|---|---|
| `git diff --check` | PASS — no whitespace errors |
| `ruff format --check .` | PASS — 117 files already formatted |
| `ruff check .` | PASS — all checks passed |
| `mypy --explicit-package-bases app` | PASS — no issues in 57 source files |
| `pytest` | PASS — **350 passed**, 16 warnings, 0 failed |
| `pnpm env:validate` | PASS |
| `pnpm security:audit` | PASS |
| `make migration-check` | PASS — Alembic head `0006_field_reviews` |
| `make docker-check` | PASS — compose config valid |

## Frontend

| Command | Result |
|---|---|
| `pnpm --filter @advs/web lint` | PASS |
| `pnpm --filter @advs/web typecheck` | PASS |
| `pnpm --filter @advs/web test` | PASS — 94 passed, 9 files |
| `pnpm --filter @advs/web build` | PASS |

## Test count movement

| State | Backend tests |
|---|---|
| Before P0 edits | 340 |
| After the P0 range, before this validation | 347 |
| After this validation | **350** |

The three added tests cover the oversized-page-box rejection, the guarantee that
a page already within budget is not downscaled, and the guarantee that a vector
page is never downscaled to a source resolution it does not have.

## Contract conformance

`pnpm contracts:generate` was not re-run as part of this validation because
P0 changed no route signature or schema. The API surface exercised by the
frontend is unchanged; the OpenAPI document and generated contract were last
updated in `f641fee`. The frontend typecheck and build passing against the
current contract is the evidence relied on.

## Warnings

`pytest` reports 16 warnings. All are third-party deprecation notices
(`starlette.testclient` httpx shim, PyMuPDF `fitz` alias, SWIG internals,
`pythonjsonlogger` relocation). None originate in ADVS code and none affect gate
results.

## Environment

| Item | Value |
|---|---|
| Python | 3.12, project venv `apps/api/.venv312` |
| PaddleOCR / paddlepaddle | 3.2.0 / 3.1.1, CPU |
| OCR models | cached locally: `PP-OCRv5_mobile_det`, `korean_PP-OCRv5_mobile_rec`, orientation models |
| Network use during evaluation | none for OCR; models served from the local cache |
| Database | SQLite for the harness runs; scratch instance for the live stack |
| Hardware | CPU only; no GPU |

OCR ran against genuinely cached Korean models with no network fetch, so the
results reflect real recognition rather than a stub.

## Environment validation caveat

`pnpm env:validate` and `pnpm security:audit` validate the committed
configuration contract. The evaluation itself overrode `DATABASE_URL`,
`STORAGE_PATH` and `PADDLE_OCR_CACHE_DIR` to point at scratch directories and
the local model cache. Those overrides are how the runs were isolated; they do
not weaken the committed configuration.