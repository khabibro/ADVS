# Test results

Final gate run on the completed P0 tree. Every command was executed; results are
reproduced in `quality_gates.md` with full detail.

## Backend gates

| Command | Result |
|---|---|
| `git diff --check` | PASS |
| `ruff format --check .` | PASS — 117 files formatted |
| `ruff check .` | PASS |
| `mypy --explicit-package-bases app` | PASS — 57 source files |
| `pytest` | PASS — **350 passed**, 16 warnings, 0 failed |
| `pnpm env:validate` | PASS |
| `pnpm security:audit` | PASS |
| `make migration-check` | PASS — head `0006_field_reviews` |
| `make docker-check` | PASS |

## Frontend gates

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
| After the P0 commit range, before final validation | 347 |
| After final validation | **350** |

## Behavioural validation outside the unit suite

| Area | Checks | Result |
|---|---|---|
| Live HTTP end-to-end | 43 | all substantive checks pass |
| Suspected-failure verification | 19 | all pass after the harness bugs were corrected |
| F-13 / F-14 / F-15 / F-16 / F-17 | 48 | 48 pass, 0 fail |
| Real-document corpus run | 7 documents | 7 processed, 7 classified, False READY 0 |

The 48-check regression suite exercises the real PaddleOCR provider: multi-page
fixtures at 1, 3 and 6 pages, a forced per-page timeout and subsequent recovery,
three concurrent OCR calls, logging isolation across real PaddleOCR
initialisation, review closure across all eight supported document types, and
comparison semantics through the real verification engine.

## Warnings

16 pytest warnings, all third-party deprecation notices (`starlette.testclient`
httpx shim, PyMuPDF `fitz` alias, SWIG internals, `pythonjsonlogger`
relocation). None originate in ADVS code.
