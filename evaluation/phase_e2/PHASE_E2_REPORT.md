# Phase E2 report — Part A: applicant and reviewer flows (2026-10-10)

Branch `phase-e2/uiux` → merged into `main` with `--no-ff`; tag **`midterm-demo-v2`** on the merge commit. The tag `midterm-demo-2026-10-14` is unchanged. No classification, extraction, validation, auto-acceptance or scorer logic was changed.

## 1. Audit summary (`UX_AUDIT.md`)
32 problems found by walking every flow and edge state at 1440×900 and 390×844 (screenshots in `evaluation/phase_e2/audit_screenshots/`): **4 blocker, 17 major, 10 minor, 1 to measure** — 29 planned for Part A, 3 for Part B.
- **11 accuracy defects** (the UI showed something the API did not say). The worst: a requirement row said "분석 완료" while the check said 보완 필요; "필수 서류 4 / 4", "확인 필요 N건" and the 4-step progress bar were computed in the browser; the web app accepted only PDF while the backend accepts PDF, PNG, JPEG and WEBP.
- **21 usability problems.** The worst: after the last review the screen read "점검 전" and the reviewer had to find 자동 점검 실행; no banner saying what the status means and what to do; the empty submission looked like a finished check; row upload buttons did not upload to the row; the same finding was listed twice.

## 2. What was fixed in Part A (before → after)
Before screenshots are the v1 screens; after screenshots are the v2 screens (`docs/midterm/screenshots_v2/before|after/`, also at 1920×1080 and 390 px).
| Area | Change | Before → after |
|---|---|---|
| Result screen | Status banner: label, one sentence with the API's N ("아래 1개 항목을 보완해 주세요"), next step, 점검 기준일 with its explanation; 제출 가능 always says "(공식 승인 아님)" | `before/D2_workspace.png` → `after/1280x720/D2_workspace.png` |
| Requirement checklist | One row per document, state from the API (제출됨 · 확인 완료 / 보완 필요 / 확인 필요 / 미제출 / 분석 중 …), file names, the issues for that row, upload or replace in the row | `before/D8_workspace.png` → `after/1280x720/D8_workspace.png` |
| Issues | Grouped by severity: what is wrong with the real values, which document and field, how to fix, link to the evidence | `before/D3_workspace.png` → `after/1280x720/D3_workspace.png` |
| Evidence | Document page: the original next to the fields, boxes outlined, click a field or a box; source badges (디지털 원본 / 자동 확인 — reason / 확인 필요 / 담당자 확인 / 담당자 수정); fields no rule uses are "참고 항목" | `before/D6_document_detail.png` → `after/1280x720/D6_document_detail.png` |
| Review | "확인할 항목 N개", "x / y 완료", the cropped original (label and value outlined) with the reason, Enter to confirm, 값 수정 (type, Enter, Esc), 판단 불가, focus moves to the next item | `before/R1_review_needed.png` → `after/1280x720/R2_review_list.png` |
| After the last item | The check re-runs by itself; the banner changes and says "방금 확인 필요 → 제출 가능(으)로 바뀌었습니다"; the manual re-check stays under the banner | `before/R4_ready_after_review.png` → `after/1280x720/R4_ready_after_review.png` |
| Upload | Starts on selection; accepted types and size from the API (photos included); per-row upload; 업로드 중 → 분석 중 with elapsed seconds and the expected time; cause-specific errors; a file recognised as another type says so | `before/U2_upload_processing.png` → `after/1280x720/U1_processing.png`, `E1_corrupt_file.png`, `E2_unsupported_type.png` |
| Empty submission | One calm state: "필요한 서류 N종을 업로드해 주세요"; no check or review panels | `after/1280x720/U0_empty_submission.png` |
| List | Each card: status, item count, progress | `before/00_projects_list.png` → `after/1280x720/00_projects_list.png` |
| Wording | One term for a submitted paper (서류, not 문서); typo in the site description | – |

## 3. API additions (read-only unless noted) and their tests
All additions aggregate decisions that already exist; none decides anything (`apps/api/tests/test_phase_e2_*.py`, 21 tests).
| Endpoint / field | Purpose | Tests |
|---|---|---|
| `GET /projects/{id}/overview` | check state, status item count, per-requirement state, next step, deduplicated issues with their values, review progress, other files | empty, unchecked, ready, mismatch, expired, missing, in flight, unrecognised/foreign files, dedup, 404, read-only behaviour |
| `GET /project-summaries` | list screen | matches the overview |
| `GET /upload-rules` | allow-list, size, pages | equals `ALLOWED_EXT` |
| `GET /documents/{id}/pages`, `/pages/{n}/image` | page image | PDF and photo, 404s |
| `EvidenceRead.normalized_box` | box as fractions of the page, only when the coordinate system is known (rotated pages and unknown systems return none) | embedded-text, OCR with render scale, omitted cases |
| `FieldRead.used_by_rules` | fields that can change the status | API test |
| `get_latest(read_only=True)` (behaviour fix) | the overview takes no lock and writes nothing | stale check is left for the writer |
| SQLite WAL + 30 s busy timeout (infra fix) | polling during an analysis made `POST …/process` fail with "database is locked" (found by the upload E2E test) | `test_phase_e2_sqlite_concurrency.py` |

## 4. Test and accessibility results (2026-10-10)
| Gate | Result |
|---|---|
| Backend: ruff, format, mypy; pytest | clean; **555 passed** |
| Frontend: lint, typecheck, build; vitest | pass; **107 passed** (12 files) |
| End-to-end (Playwright, real API and web app) | **15 of 15**: D1, D2, D5, D8 (inline upload), D6 (keyboard review → automatic 제출 가능), a correction, upload errors, a JPG photo, accuracy, no raw enum, list = screen, axe, projector sizes |
| Unit test on copy | every issue code the check can return has Korean text and a fix hint (fails if one is missing) |
| Accessibility (axe, WCAG 2.0/2.1 A and AA) | **0 serious or critical violations** on the list, new submission, D1, D2, D5, D6 and a document page at desktop width; list, D6, D2 at 390 px |
| Accuracy test | for D1–D8 the banner label and count, every requirement row's state, and the issue/review counts equal the overview response; the list status equals the submission screen |
| Layout | no horizontal scroll at 1280×720, 1920×1080 and 390 px on the demo screens |

## 5. Rehearsal (`make demo-rehearsal`, final code, three runs in a row, each starting with a reset)
| # | Scenario | Run 1 / 2 / 3 | Time (s) |
|---|---|---|---|
| D1 | B01 digital | PASS PASS PASS | 0.2 |
| D2 | expired tax certificate | PASS PASS PASS | 0.2 |
| D3 | company mismatch | PASS PASS PASS | 0.2 |
| D4 | four name notations | PASS PASS PASS | 0.2 |
| D5 | 지방세 look-alike | PASS PASS PASS | 0.2 |
| D6 | scanned + review | PASS PASS PASS | 62.5–63.1 |
| D7 | student | PASS PASS PASS | 0.1–0.3 |
| D8 | missing document | PASS PASS PASS | 0.2 |
| ui | browser: screens equal the API | PASS PASS PASS | 7 |
The rehearsal now also compares the overview with the check for every scenario, models the automatic re-check (after the last confirmation the overview must say "run the check", then "done"), and runs the browser accuracy test at the end (`--no-ui` skips it). It failed twice before it passed, for reasons found and fixed in this phase: the `make` target used the wrong virtualenv path, and the SQLite lock above.

## 6. Tags
- **`midterm-demo-v2`** — Part A (this branch merged into `main`).
- **`midterm-demo-2026-10-14`** — v1, unchanged.
Present from v2 if you want the clearer screens; present from v1 (`git checkout midterm-demo-2026-10-14`, script `DEMO_SCRIPT_v1.md`) if you prefer the version already rehearsed in Phase E. Both pass their rehearsal.

## 7. Git identity used
- **Author of every commit:** `Munira <munira@knu.ac.kr>` (repository-local config); **pushing account:** `munira117` via the SSH alias `github-munira` (`ssh -T` greeted munira117; pushes were accepted).
- **Values before the change:** `user.name KHABIBILLO`, `user.email khabibillionaire@gmail.com`, `origin git@github-khabibro:khabibro/ADVS.git`. The global Git configuration was not touched.
- **No AI attribution:** none of the commits carries a Claude or "Co-Authored-By" line (checked with `git log --format=%B`).
- **Commits:** 34 on the branch, including the one that adds this report (33 before it); list below. Two process notes: the commit that makes the check automatic has a stray Chinese character in its subject ("点검 전", message only, not rewritten because it was already pushed); and for two commits I staged whole directories with explicit paths (`git add -A <path>`) instead of single files.
- `b1611ad` docs: UX audit of the applicant and reviewer flows with screenshots
- `3274c57` feat(api): project overview read model for the submission screen
- `27f4707` feat(api): publish the upload allow-list at GET /upload-rules
- `7c2d262` feat(api): page images and normalised evidence boxes
- `9aa6003` chore(contracts): regenerate OpenAPI types for overview, upload rules and pages
- `b691e3f` feat(api): fields report whether a workflow rule uses them
- `065fda2` feat(api): project summaries for the submission list
- `ce9c81f` chore(contracts): regenerate OpenAPI types from this branch's API
- `adbcef6` feat(web): API client and queries for overview, upload rules and page images
- `e1374f9` feat(web): Korean copy for issues, requirement states and the status banner
- `0fc6088` feat(web): uploader that starts on selection and follows the API's allow-list
- `c6ecd28` feat(web): submission screen built on the overview read model
- `25838b0` fix(web): re-run the check automatically instead of showing 点검 전
- `c61ee50` feat(web): review list with the original beside each value
- `a20fd07` feat(web): one source badge per field, built from the API's fields
- `7c9a0f7` feat(web): document detail with the page image and highlighted evidence
- `2679013` feat(web): submissions list shows status, item count and progress from the API
- `41d5fe0` fix(web): typo in the site description
- `b02b0fa` fix(web): connection error says what to do
- `a4d31ab` fix(web): show the label and the value together; issues before the upload area
- `e284d91` fix(api): the overview is read-only so polling cannot block an analysis
- `805afab` fix(api): SQLite runs in WAL mode with a 30 s busy timeout
- `2c577fa` test(web): end-to-end flows, accessibility and accuracy checks
- `2f67c31` fix(demo): reset also removes the SQLite WAL files
- `8dc4df6` fix(web): one term for a submitted paper everywhere: 서류
- `723c045` test(demo): rehearsal asserts the overview, models the automatic re-check, runs a UI smoke test
- `b21a2e5` fix(web): the automatic re-check keeps the date of the earlier check
- `8818cff` chore(demo): screenshot flow for the new review, upload and error screens
- `ba602c8` fix(web): document detail shows the unconfirmed machine value and all evidence text
- `2734ee6` docs: demo script for the v2 interface (v1 kept)
- `c6805c5` fix(demo): make demo-rehearsal uses the API virtualenv under apps/api
- `c008ffc` docs: UX audit resolution at the end of Part A
- `84f1499` docs: v2 screenshots (before/after, 1280x720, 1920x1080, 390 px), updated test counts

## 8. Switch the repository back to Khabibillo's identity (for backend work such as D3)
Run these yourself:
```bash
git config --local user.name "KHABIBILLO"
git config --local user.email "khabibillionaire@gmail.com"
git remote set-url origin git@github-khabibro:khabibro/ADVS.git
```

## 9. Open decisions and what is left
- **Part B (after 2026-10-14):** reviewer queue across submissions (UX-20), admin checklist/rules screen with safety warnings (UX-19), submission history and audit view (UX-21), usability test with 3–5 classmates (`USABILITY_TEST.md`), and the two partly-fixed items (the native date picker's locale; long phone pages).
- **D3 is still unmerged.** The D3 merge attempt stopped because D3 changes demo D6 (the scanned submission now reaches 제출 가능 without a reviewer). That decision is open and independent of this phase; when D3 is merged, D6 in the demo, in `scripts/demo_scenarios.py` and in `ui-flows.spec.ts` needs a scenario that still requires a review. The D3 branch carries the same one-line `Makefile` fix.
- Not tested end to end: a multi-document PDF through the new screen (covered by the same API state mechanism), and the admin app (unchanged placeholder).
