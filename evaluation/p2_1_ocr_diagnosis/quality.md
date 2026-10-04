# Quality Gates

Every gate was run at the end of P2.1. Nothing was weakened to make anything
pass. No production file was modified, so no test could have needed changing.

## Results

| Gate | Command | Result |
|---|---|---|
| Backend tests | `pytest` (apps/api) | **PASS — 368 passed**, 16 warnings, 27.3 s |
| Backend lint | `ruff check apps/api` | **PASS — all checks passed** |
| P2.1 script lint | `ruff check evaluation/p2_1_ocr_diagnosis` | **PASS — all checks passed** |
| Formatting | `ruff format --check apps/api evaluation/p2_1_ocr_diagnosis` | **PASS — 131 files already formatted** |
| Backend typecheck | `mypy --explicit-package-bases app` | **PASS — no issues in 63 source files** |
| Frontend lint | `pnpm lint` | **PASS — 4/4 tasks** |
| Frontend typecheck | `pnpm typecheck` | **PASS — 4/4 tasks** |
| Frontend tests | `pnpm test --filter @advs/web` | **PASS — 94 passed, 9 files** |
| Frontend build | `pnpm build` | **PASS — 4/4 tasks** |
| Migration check | `make migration-check` | **PASS — upgrade head OK, single head `0006_field_reviews`** |
| Environment validation | `pnpm env:validate` | **PASS** |
| Security audit | `pnpm security:audit` | **PASS** |
| Docker config | `make docker-check` | **PASS — exit 0** |
| Whitespace | `git diff --check` | **PASS — exit 0** |

## Notes

**Frontend test count.** `pnpm test` at the workspace root reports "no tests
yet" for `@advs/ui` and `@advs/admin`; the 94 real tests are `@advs/web`'s.
The 368 backend / 94 frontend split matches the P2 report.

**`mypy` needs its flag.** Running `mypy app` from `apps/api` fails with
*"Source file found twice under different module names"* because of how the
package root is resolved. The Makefile target
`api-typecheck` passes `--explicit-package-bases`, and that invocation is
clean. The bare invocation failing is a pre-existing invocation quirk, not a
type error, and not something P2.1 changed.

**Docker image build was not run.** `make docker-check` validates the compose
configuration and exits 0. An actual `docker compose build` was not attempted
in this phase, so image buildability is **not claimed**. P2 recorded a
successful build on an escalated retry; this phase makes no new claim either
way.

**Six P2.1 scripts were brought to zero lint findings.** An earlier revision
of the diagnostic engine compared recognised text against gold with raw string
equality, which mis-classified correct readings as recognition errors — a
hyphenated business number and a letter-spaced date both read as failures. The
comparison key was fixed to be format-insensitive, and the diagnosed
distribution has been identical across three consecutive runs since. This is
noted because a lint-and-format pass on the diagnostic code is what surfaced
the unused-variable dead code next to the faulty comparison.

## Repository state

| Property | Value |
|---|---|
| Branch | `main` |
| HEAD at start | `48e3824a780e3c051cba2d2eb1838851db1fcf1e` |
| HEAD at end | `48e3824a780e3c051cba2d2eb1838851db1fcf1e` |
| Tracked files modified | **0** |
| Tracked diff / diff --stat | **empty** |
| Commits made | **0** |
| Pushes made | **0** |
| Git history rewritten | **no** |
| Git identity or config changed | **no** |

The only change to the tracked tree is the new untracked directory
`evaluation/p2_1_ocr_diagnosis/`. All pre-existing untracked P1/P2 artifacts
were left untouched.

## Corpus and private-data integrity

| Check | Result |
|---|---|
| Originals byte-identical (SHA-256) | **7/7** |
| Originals unchanged in size | **7/7** |
| Originals unchanged in mtime | **7/7** |
| Originals moved / renamed / overwritten | **no** |
| Private runtime directory ignored by Git | **yes**, verified with `git check-ignore` |
| Private files appearing in `git status` | **0** |
| Private OCR text or values in tracked artifacts | **none** |
| Private filenames or paths in tracked artifacts | **none** |
| Cloud provider or external LLM/VLM used | **no** |
| Dependencies added or changed | **none** |

## What was not verified

- Docker **image build** (compose config validated only).
- Frontend tests for `@advs/ui` and `@advs/admin` — they do not exist yet, so
  "4/4 tasks successful" means four echo statements, not four test suites.
- Any load, soak or endurance behaviour.
- Behaviour on the 30-page maximum, or on documents with an embedded text
  layer, or on genuinely out-of-scope real documents — the frozen corpus
  contains none of those.
