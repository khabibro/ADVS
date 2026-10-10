# Phase E2 — UX audit (2026-10-10)

Method: the demo (`scripts/demo reset`) was walked in Chromium with Playwright (`scripts/ux_audit.mjs`) at **1440×900** and **390×844**; screenshots are in `evaluation/phase_e2/audit_screenshots/<size>/`. Flows: choose workflow → empty project → upload (PDF, scan, unsupported, empty, corrupt, disguised, multi-document, look-alike, duplicate) → result → issues → review → edge states (network error, not found). Console and horizontal overflow were checked on every screen: **no horizontal overflow at 1440 or 390**, no page errors. Heuristics: H1 visibility of status, H2 match with the real world, H3 user control, H4 consistency, H5 error prevention, H6 recognition over recall, H7 efficiency, H8 helpful errors. Severity: blocker / major / minor. Plan: **A** = by 2026-10-13, **B** = after the midterm.

## 1. Accuracy defects — the UI shows something the API did not say (top priority)
| # | Where (code) | What the UI does | Why it is wrong | Sev | Fix | Plan |
|---|---|---|---|---|---|---|
| AC-1 | `lib/document-slots.ts` `slotPresentation`, `RequirementSlotCard` | Requirement chip says "분석 완료" from the processing status | D2: the expired 납세증명서 row says **분석 완료** while the check says 보완 필요 (`03_D2_workspace.png`). Row state must be the backend's decision | blocker | API: per-requirement `state` in a project overview; UI renders it | A |
| AC-2 | `ProjectWorkspacePage`, `DocumentWorkspace` | "필수 서류 4 / 4" counted client-side from classification + processing | counts documents that exist, not requirements the check accepted; stays 4/4 with a mismatch | major | API counts (`requirements_total/ok/missing`) | A |
| AC-3 | `ProjectWorkspacePage`, `ReviewSection` | "확인 필요 N건", "N개 항목을 확인하면…" are `reviewItems.filter(...)` in the browser | count is the UI's own; must be the API's | major | API `pending_review_count` | A |
| AC-4 | `ProjectWorkspacePage` `activeStep` | 4-step progress inferred from document statuses | the "current step" is a guess (can show step 1 while step 3 is done) | major | API `next_step` code | A |
| AC-5 | `ProjectWorkspacePage` `displayedStatus` | synthesises "점검 전" when the stored check is stale | after the last review the project reads "점검 전" although all inputs are resolved (see UX-1) | major | API `check_state` (CURRENT / STALE / NEVER_RUN); auto re-run | A |
| AC-6 | `document-slots.ts` `hasMultiple`, overflow note | "같은 종류 서류가 N개 인식되었습니다" from document counts | the backend decides (duplicate notice, `MULTIPLE_DOCUMENTS_REQUIRE_REVIEW`); the UI pre-empts it. Same file twice shows "3개 인식" (`15_same_document_twice.png`) | minor | render API issues/notices only | A |
| AC-7 | `VerificationSection` `IssueEvidence` (Phase E) | quotes the values by fetching each document and picking fields | values composed in the browser; one extra request per card | major | API puts `value`, `related_value`, `reference_date` on each issue | A |
| AC-8 | `lib/upload-queue.ts` `validatePdfFile`, input `accept=` | rejects everything but PDF ("PDF 파일만 선택할 수 있습니다") | the backend accepts PDF, PNG, JPG, WEBP (`services/storage/local.py` `ALLOWED_EXT`); photos are rejected before they reach it (`11_jpg_image_selected.png`) | blocker | read the allow-list from the API; accept the same files | A |
| AC-9 | `ProjectsListPage` | status chip from `project.status`; "필수 서류 N종" | list cannot say stale / needs review / why | minor | list items get the same overview summary | A |
| AC-10 | `DocumentDetailPage` | document chip + validation list computed per document | separate from the submission result; users cannot tell which one counts | minor | label as "이 서류 자체 점검"; link the submission result | A |
| AC-11 | `app/layout.tsx` | metadata description "…제출 전 자동 점겁니다." | typo | minor | fix | A |

## 2. Usability problems
| # | Screen / state | Problem | Heuristic | Sev | Planned fix | Plan |
|---|---|---|---|---|---|---|
| UX-1 | review → result | After the last confirmation the status becomes **"점검 전"** and the user must find and press 자동 점검 실행 (`R3` in `docs/midterm/screenshots`) | H1 H7 | blocker | re-run the check automatically after the last item; show "확인 필요 → 제출 가능"; manual button stays secondary | A |
| UX-2 | result | Only a small chip and a 4-step bar: no banner saying what the status means and what to do next | H1 H6 | blocker | status banner with sentence + N + next step | A |
| UX-3 | empty / new project | "점검 전", "확인 필요 0건", "직접 확인할 항목 — 확인이 필요한 항목이 없습니다" and "아직 점검을 실행하지 않았습니다" all at once (`10_empty_project.png`): looks like a finished check with nothing to do | H1 H2 | major | one calm empty state: "필요한 서류 4종을 업로드하세요", no review/check panels until there is something | A |
| UX-4 | requirement rows | Each row has a "PDF 업로드" button that only scrolls to a generic input; the file is not tied to the row | H2 H7 | major | per-row upload that opens the file chooser; the generic drop zone maps files by the detected type | A |
| UX-5 | upload | While analysing, only a tiny "분석 중" pill; no time expectation (a scan takes ~15 s per page) (`13_processing_scanned.png`) | H1 | major | stages 업로드 중 → 분석 중 + "스캔 문서는 페이지당 약 15초" + elapsed time | A |
| UX-6 | upload failure | Green "1개 파일을 추가했습니다" is shown together with a red failure; generic "목록에서 파일 이름을 확인하고 다시 시도해 주세요" with no guidance per cause (`12_corrupt_pdf_result.png`) | H8 | major | one message per cause with what to do (corrupt: re-save/re-scan; empty; wrong type; too large; duplicate) | A |
| UX-7 | result | The same finding appears twice: in "확인된 항목" and again in "직접 확인할 항목" (`D6`); on a phone this is 4 identical cards before the review list (`390x844/03_D6_workspace.png`) | H4 | major | issues once, grouped by severity; review list is the action area | A |
| UX-8 | issue cards | Generic action text per code ("기준 서류와 다른 값을 직접 확인해 주세요"), no concrete fix, no evidence link, no document name for the file | H8 H6 | major | "what is wrong / which document+field / how to fix" + link to evidence | A |
| UX-9 | document detail | No page image; evidence is only text; no highlight of where the value was read | H6 | major | page image beside the field table; selecting a field highlights its box | A |
| UX-10 | fields | Source badges are inconsistent: "자동 인식", "확인 필요", "직접 확인 필요", "자동 사용 가능" | H4 | major | one source badge set: 디지털 원본 / 자동 확인 — reason / 확인 필요 — reason / 담당자 확인 / 담당자 수정 | A |
| UX-11 | review | No progress ("3 / 7 완료"); four radio options + reviewer + memo on every item; no keyboard flow | H7 | major | list with progress; 확인 (Enter) / 수정 (input + Enter) / 판단 불가; keyboard friendly | A |
| UX-12 | check date | "점검 기준일" shows `10/05/2026` (US order) with no explanation | H2 | minor | Korean date format + one-line explanation | A |
| UX-13 | multi-document PDF | A 2-certificate PDF shows "분석 완료" in the 사업자등록증 row; the warning only exists after a check (`12_multi_two_certs_result.png`) | H1 | major | covered by AC-1 (state from the API after the automatic check) | A |
| UX-14 | unknown document | "문서 확인 필요" file card is good, but the missing requirement is not tied to it | H6 | minor | link the unknown file to the missing requirement in the banner/checklist | A |
| UX-15 | network error | "서버에 연결할 수 없습니다." with retry only (`20_network_error_list.png`) | H8 | minor | add what to do (check connection / try again) | A |
| UX-16 | mobile | No overflow, but file names truncate to ~6 characters and the page is ~4500 px tall | H7 | minor | allow 2-line file names; shorter sections after UX-7 | A |
| UX-17 | projects list | Cards show only a status chip: no count of issues/reviews, no next step | H1 | minor | add the overview summary line | A |
| UX-18 | accessibility | Not yet measured | – | – | axe on main screens in Part A tests | A |
| UX-19 | admin app | Empty placeholder (`/` and `/projects` show one heading) | H2 | major | checklist/rules screen | **B** |
| UX-20 | reviewer | No queue across submissions; reviewer opens submissions one by one | H7 | major | review queue with filters | **B** |
| UX-21 | history | No view of who confirmed or corrected what | H1 | minor | audit view | **B** |

## 3. What already works
Korean status labels, plain disclaimer wording, no raw enums, retry on load errors, drag-and-drop, queue protection against double clicks, per-file failure isolation, no horizontal overflow at 390 px.

## 4. Fix order
AC-1…AC-8 and UX-1, UX-2 first (they share one API addition: the project overview), then UX-4…UX-8, UX-9, UX-10, UX-11, then the rest, then tests and accessibility.

## 5. Resolution at the end of Part A (2026-10-10)
Tests named below are in `apps/web/e2e/ui-flows.spec.ts` (E2E), `apps/web/src/**/*.test.ts(x)` (unit) and `apps/api/tests/test_phase_e2_*.py` (API).

| # | Result | How / evidence |
|---|---|---|
| AC-1 row state | **fixed** | `GET /projects/{id}/overview` returns `requirements[].state`; the row shows it. E2E "every screen shows exactly what the API decided" |
| AC-2 counts | **fixed** | `counts.required_ok/required_total` from the API |
| AC-3 review count | **fixed** | `counts.review_open/review_done` (progress "3 / 7 완료") |
| AC-4 next step | **fixed** | `next_step` code from the API; the 4-step bar is gone |
| AC-5 "점검 전" | **fixed** | `check_state`; the check re-runs by itself (`use-auto-check`), E2E D6 |
| AC-6 duplicates inferred | **fixed** | the screen shows only API issues and notices; the same finding is reported once by the API (`_unique`) |
| AC-7 values on issues | **fixed** | `issues[].value/related_value/reference_date/expected_value/max_age_days`; no extra requests |
| AC-8 allow-list | **fixed** | `GET /upload-rules`; E2E "a photo (JPG) is accepted" |
| AC-9 list | **fixed** | `GET /project-summaries` on the list (unit + E2E) |
| AC-10 per-document chip | **fixed** | labelled "이 서류 자체 점검"; submission result is the banner |
| AC-11 typo | **fixed** | |
| UX-1 manual re-check | **fixed** | E2E D6: Enter ×4, banner turns 제출 가능, "방금 확인 필요 → 제출 가능" |
| UX-2 banner | **fixed** | status, sentence with the API's N, next step, 점검 기준일 with its explanation |
| UX-3 empty state | **fixed** | an untouched submission shows "필요한 서류 N종을 업로드해 주세요" and no check/review panels (`U0_empty_submission.png`) |
| UX-4 row upload | **fixed** | per-row 업로드 / 새 서류로 교체; E2E D8; a file the backend recognises as another type says so |
| UX-5 processing | **fixed** | 업로드 중 → 분석 중 with elapsed seconds and the expected time (`U1_processing.png`) |
| UX-6 failure copy | **fixed** | one cause-specific message with what to do; E2E "a file the backend cannot read…" |
| UX-7 repeated issues | **fixed** | issues once, grouped by severity; review items only in the review list |
| UX-8 issue text | **fixed** | what is wrong · document and field · 해결 방법 · 근거 보기 link; unit test fails if an issue code has no Korean text or fix |
| UX-9 evidence | **fixed** | page image with highlighted boxes; the review list crops the original (label and value) |
| UX-10 badges | **fixed** | 디지털 원본 / 자동 확인 — reason / 확인 필요 / 담당자 확인 / 담당자 수정; fields no rule uses are "참고 항목" |
| UX-11 review | **fixed** | progress, Enter to confirm, 값 수정 (type, Enter, Esc), 판단 불가, focus moves to the next item |
| UX-12 date format | **partly** | the date is shown in Korean format with its explanation; the native date picker inside "날짜를 바꿔 다시 점검하기" follows the browser's locale |
| UX-13 multi-document PDF | **covered, not separately tested** | the row state comes from the API after the automatic check; the F13 file was not re-run end to end |
| UX-14 unknown file | **fixed** | "확인이 필요한 파일" with the reason; the missing requirement row says 미제출 (E2E D5) |
| UX-15 network error | **fixed** | "네트워크 연결을 확인하고 다시 시도해 주세요" |
| UX-16 mobile | **partly** | file names wrap, no horizontal scroll (E2E at 390 px); the page is still long with four review cards |
| UX-17 list | **fixed** | |
| UX-18 accessibility | **fixed** | axe (wcag2a/2aa/21a/21aa): 0 serious or critical violations on list, new submission, D1, D2, D5, D6 and a document page at desktop width; list, D6, D2 at 390 px |
| UX-19 admin, UX-20 reviewer queue, UX-21 history | **B** | Part B (after the midterm) |

### Found while building Part A (not in the audit above)
- **SQLite lock:** polling the overview while a document was analysed made `POST /documents/{id}/process` fail with "database is locked" (the upload E2E found it). The overview is now read-only (`get_latest(read_only=True)`) and SQLite runs in WAL mode with a 30 s busy timeout.
- **Evidence crop** showed only the label; it now spans every evidence box (label and value).
- **Duplicate error text** (message and detail identical) removed from the review item error.
- **Check date:** after a review the API no longer knows the earlier date (the stored check is invalidated), so the screen remembers it for the automatic re-check.
- `make demo-rehearsal` itself pointed at the wrong virtualenv path (never run through `make` before).
