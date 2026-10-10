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
