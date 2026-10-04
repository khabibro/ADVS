# System State — recorded at the start and verified at the end

## Repository

| | |
|---|---|
| Branch | `main` |
| HEAD | `721cc9d` — *"Improve real-document processing and extraction"*, Tue Sep 29 09:37:36 2026 +0900 |
| Upstream | `origin/main` = `origin/HEAD` = same commit. **Nothing unpushed.** |
| Remote | `git@github-munira:khabibro/ADVS.git` |
| Git identity (read-only, never modified) | `Munira <munira@knu.ac.kr>` |
| Modified tracked files at start | **45** (1,553 insertions, 323 deletions) |
| Untracked files at start | **13** (5 new backend modules, 1 eval lib, 1 operational script, 6 new test files) |
| `git diff --check` at start | clean |

The working tree contained substantial uncommitted backend work (a new OCR worker, a project-lock
service, a document-validation service, a requirements service, an evaluation safety scorer, and six
new test files). **All of it was preserved untouched.**

## Baseline commit history

```
721cc9d Improve real-document processing and extraction      <- HEAD
2228b75 Rebuild frontend document workflow and review experience
6a73d37 Add evidence-aware human review workflow
95820f8 Add null-safe submission verification engine
d22ce4e Harden document classification and field extraction
2638c51 Integrate end-to-end document processing pipeline
237404b Add canonical document evidence and provenance
5270935 Complete document domains
88f227a Complete status semantics
```

## Environment

| | |
|---|---|
| OS | macOS 26.6.2 (build 25G83) |
| CPU / RAM | 11 cores / 18 GiB |
| Docker | running, Compose v5.5.1 |
| Python | 3.12 in `apps/api/.venv312` |
| Database used | SQLite (fresh, outside the repo); migrations 0001→0006 applied |
| OCR | PaddleOCR **3.2.0** + PaddlePaddle 3.1.1, CPU, `korean_PP-OCRv5_mobile_rec` + `PP-OCRv5_mobile_det`, models already cached |
| External services used | **none.** No document, OCR text or field value left the machine. |

## Stack verdict

- `docker compose build api` → **succeeded** (`Image advs-api Built`, exit 0).
- Functional evaluation ran on the repository's supported **local development path** with real
  uvicorn and a real socket, because that path uses the already-cached Korean OCR models and the
  container would have to re-download them.
- Reported as: **LIVE STACK (local backend) + DOCKER IMAGE BUILD VERIFIED.**

## Behavioural check totals

| Suite | Result |
|---|---|
| Realistic-document HTTP baseline | 7 documents; 6 COMPLETED, 1 rejected at upload |
| Behavioural checks (review, reprocess, duplicates, UNKNOWN, READY, null safety, API, security) | **44 PASS / 5 FAIL / 6 INFO** |
| Concurrency & capacity checks | **4 PASS / 2 FAIL** |
| Mixed-PDF routing & provenance | **5 PASS** |
| Pure-function normalisation/date probes | **56 PASS / 1 FAIL** (the failure was the probe's own incorrect expectation of a documented behaviour) |
| Quality gates | 12 PASS, **2 CODE FAILURES** (`pytest` 2 failed; `ruff format --check` 3 files) |

## Git state after the audit — VERIFIED

```
$ git status --short
 M .gitignore                                        (pre-existing)
 M apps/api/app/api/v1/routes.py                     (pre-existing)
 ... 43 further pre-existing modifications ...
?? apps/api/app/document_intelligence/ocr/worker.py  (pre-existing)
 ... 12 further pre-existing untracked paths ...
?? evaluation/real_backend_validation/               (NEW — sanitized artifacts only)

$ git diff --stat
 45 files changed, 1553 insertions(+), 323 deletions(-)   <- identical to the start

$ git diff --check
 (clean)
```

- **No commit.** HEAD is still `721cc9d`.
- **No push.** Working tree is still ahead of nothing unpushed.
- **No reset, rebase, force checkout or clean.** No existing change was discarded.
- **No Git identity was modified.**
- **No original document was modified, renamed, moved or deleted.** All were opened read-only.
- **No realistic document was copied into the repository.** Every artifact under
  `evaluation/real_backend_validation/` passed an automated PII assertion before being written; the
  ground-truth values and rendered pages live in a directory outside the repository.
- **No production source file was modified.** One temporary probe file (`apps/api/_probe2.py`) was
  created during a logging investigation and removed immediately; the diff was re-verified
  byte-for-byte against the pre-audit state.
- The **only** net repository change from this audit is the new, sanitized
  `evaluation/real_backend_validation/` directory.