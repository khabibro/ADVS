# Phase E report — midterm demo readiness (2026-10-10)

Branch `phase-e/midterm-demo`, merged into `main` with `--no-ff`, tag `midterm-demo-2026-10-14`. Feature freeze observed: no change to classification, extraction, validation, auto-acceptance policy or scorer.

## 1. Baseline decision
**Phase D3 was not merged.** `phase-d3/internal-automation` has no phase report or acceptance table, and its own comparison (`evaluation/phase_d3/D3_configs.md` on that branch) shows a false 제출 가능 in the extended injection suite (case E3c-both on hold-out-2 data, configurations C1c/C4/C5). The branch and its one uncommitted file (`evaluation/phase_d/holdout_runs.log`) were left untouched (Phase E was built in a separate git worktree off `main`). **D3 continues after the midterm.** The demo runs on `main` = Phase D + D2 (final policy).

## 2. Start and reset
| Command | Does |
|---|---|
| `make demo` | first run: reset + pre-load D1–D8; then start API (:8000), web (:3000), admin (:3002); waits for "OCR model ready" |
| `make demo-reset` | stop, new database + files, seed workflows (mentor checklists incl. student 90-day rule, student number required), pre-load D1–D8, start. Idempotent: the same eight projects, same statuses, each time |
| `make demo-rehearsal` | reset, then re-run D1–D8 live through the real API with assertions, print PASS/FAIL + time |
| `make demo-stop` | stop everything |
State and logs: `storage/demo/`. Local processes + SQLite (Docker is not running on this Mac and is not needed). The OCR model is warmed up at API start (`OCR_WARMUP=true`, `app/document_intelligence/ocr/warmup.py`); measured warm-up 7–13 s with cached models, 50.8 s on a fresh checkout that had to download them.
**Clean-start check:** a fresh git worktree + new venv + `pip install -e ".[dev,paddle]"` + `pnpm install`, then `scripts/demo start` worked (models downloaded, build, D1–D8 pre-loaded). Fixed in the README: the setup never created the venv. Not committed in git and therefore needed in a fresh clone: the generated test documents (see `evaluation/datasets/synthetic/test_variants/README.md`).

## 3. Rehearsal (final committed code, three runs in a row, each starting with a reset)
| # | Scenario | Result (runs 1/2/3) | Time (s) | Actual on screen |
|---|---|---|---|---|
| D1 | B01 digital | PASS PASS PASS | 0.2 | 제출 가능 |
| D2 | B05 digital, expired tax certificate | PASS PASS PASS | 0.2 | 보완 필요; 유효기간 종료일 2026. 08. 31. |
| D3 | B03 digital, company mismatch | PASS PASS PASS | 0.2 | 보완 필요; 주식회사 테스트상사 ↔ 주식회사 가나다솔루션 |
| D4 | B02 digital, four name notations | PASS PASS PASS | 0.2 | 제출 가능 |
| D5 | B11 digital, 지방세 look-alike | PASS PASS PASS | 0.2 | **확인 필요** (not 보완 필요): document left unclassified; never 제출 가능 |
| D6 | B01 scanned + review | PASS PASS PASS | 61.9–63.2 | 확인 필요, 4 dates to a reviewer, other fields auto-accepted; after confirming through the API: 제출 가능 |
| D7 | S01 digital | PASS PASS PASS | 0.1–0.2 | 제출 가능 |
| D8 | B08 digital, 사업자등록증 missing | PASS PASS PASS | 0.2 | 보완 필요 (MISSING_REQUIRED_DOCUMENT) |
Logs per run asserted: status, issue codes, key fields (expired date before 2026-10-05, mismatch on company_name, differently written names in D4, an UNKNOWN document in D5, auto-accepted + pending fields in D6, nothing pending after review). Time = upload + analysis + check of the whole submission; D6 is four scanned pages (~16 s each, CPU OCR). **D5 differs from the brief:** the table expected an "unsupported type flagged"; the actual, truthful result is 확인 필요 with UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW. The rehearsal asserts that. No logic was changed to make any scenario pass.

## 4. UI fixes (small, frontend only; web lint, typecheck, build, 97 tests pass)
Walked every scenario in Chromium (Playwright) at 1280×720 and 1920×1080: no horizontal overflow, no raw enum, stack trace or `undefined` found. Korean status labels and the "not official approval" note already existed. Fixed:
| Problem | Fix | Before → after |
|---|---|---|
| Expired issue gave no date; mismatch no values | issue cards quote the values ("유효기간 종료일 2026. 08. 31. — 점검 기준일 … 보다 이전입니다", "A ↔ B") from the documents' fields | `screenshots_before/D2_workspace.png` → `docs/midterm/screenshots/D2_workspace.png`; D3 likewise |
| D6 listed each issue twice | the same finding is shown once | `screenshots_before/D6_workspace.png` → `D6_workspace.png` |
| Auto-acceptance invisible | badge "자동 확인 · 다른 서류와 일치 / 신청 정보와 일치 / 재판독 일치" on fields; reason "자동 확인하지 못한 이유" on fields and in the review list | `D6_document_detail.png`, `D6_workspace.png` |
| `UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW`, `ISSUE_DATE_TOO_OLD` fell back to generic text | Korean copy added | `D5_workspace.png` |
| Stale generated contract (typecheck failed after regeneration: `notices`, `NOTICE`, `auto_acceptance`) | `pnpm contracts:generate`; `notices: []` in 3 test fixtures; "참고" label | – |
Review round trip (R1–R4) and live upload (U1–U3, visible "분석 중") verified in the browser. After the last confirmation the project returns to "점검 전" and the presenter clicks 자동 점검 실행 (existing design; in the script). Tests added: `presentation.test.ts` (auto-acceptance copy), `VerificationSection.test.tsx` (date quoted, duplicates once), `tests/test_ocr_warmup.py`. Backend gates: ruff, format, mypy clean; 534 tests pass.

## 5. Bugs and gaps found, deferred (none touched, freeze)
1. Backend issue messages are generic Korean one-liners; the concrete values are composed in the UI.
2. Scanned submissions report the same date finding twice (two rules on the same field); the UI hides the duplicate, the API still returns both.
3. D5: the issue is attributed to the 국세 납세증명서 requirement while the uploaded file's type is UNKNOWN; the manifest expects 보완 필요, the system answers 확인 필요 (the scorer already accepts it).
4. Scan analysis blocks the API (OCR runs inside the request): other pages stall while a scan is being analysed; ~16 s per scanned page.
5. Web upload accepts PDF only (images work through the API).
6. Admin app is an empty placeholder; excluded from the demo.
7. No authentication; SQLite only this phase; hold-out set 3 not run; D3 unmerged.
8. The test-set README still says ADVS validates against `date.today()`; the API now takes an explicit evaluation date (the demo uses 2026-10-05).
9. Port 3000 was occupied by an unrelated dev server (another project) during development; the demo script refuses to start and says so (`WEB_PORT=3100 make demo` as a workaround).

## 6. Midterm pack
`docs/midterm/`: `RESULTS.md`, `metrics.csv`, `ARCHITECTURE_SUMMARY.md`, `DEMO_SCRIPT.md`, `ROADMAP.md`, `screenshots/` (1280×720 + `1920x1080/`: project list, D1–D8, D6 detail, review R1–R4, upload U1–U3). Tools: `scripts/demo`, `scripts/demo_scenarios.py`, `scripts/demo_rehearsal`, `scripts/demo_screenshots.mjs` (`FLOW=1` adds the review and upload shots).
