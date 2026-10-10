# ADVS midterm deck — source of every number and claim

Deck: `docs/midterm/ADVS_midterm.pptx` (PDF: `ADVS_midterm.pdf`). Paths are relative to the repository root; "§" is a section of that file. A number that is not in this table is not in the deck (checked by script, see the end). D3 figures appear only on slide 13, marked 진행 중 (unmerged).

| Slide | Number / claim on the slide (or in its notes) | Source |
|---|---|---|
| 1 | 2026-10-14 (presentation date); team, mentor and professor names | the deck brief (presentation prompt); date also `docs/midterm/RESULTS.md` heading |
| 2 | Five problem types: 누락, 만료, 불일치, 중복, 다른 서류 (other company's / look-alike) | the deck brief; matching checks in `docs/midterm/RESULTS.md` (requirements table) and `evaluation/reports/ADVS_system_audit_report.md` |
| 3 | Principle "AI는 해석하고, 증거가 뒷받침하며, 규칙이 판단하고, 불확실한 것은 사람이 확인한다" | the deck brief; project philosophy "rules decide, evidence supports, humans review" in `evaluation/reports/ADVS_system_audit_report.md` line 19 |
| 3 | 제출 가능 is not official approval | `README.md` (status paragraph); `docs/midterm/RESULTS.md` line 5; `docs/midterm/DEMO_SCRIPT.md` |
| 4 | **6** supported documents: 사업자등록증, 중소기업확인서, 국세 납세증명서, 4대 사회보험료 완납증명서 (business); 재학증명서, 성적증명서 (student) — all "implemented" | `docs/midterm/RESULTS.md` lines 10–17 (mentor requirements table) |
| 4 | Checks: missing, expiry, cross-document match, company-name notation, check digit, duplicates, look-alike, multi-document PDF | `docs/midterm/RESULTS.md` lines 12–19; `evaluation/phase_d/PHASE_D_REPORT.md` §6 (multi-document files, B09 duplicate notice); `evaluation/reports/PHASE_B_REPORT.md` (B-4 notation, look-alike) |
| 4 | **90** days issue date, student number required (student rule) | `docs/midterm/RESULTS.md` line 15; `evaluation/phase_d2/PHASE_D2_REPORT.md` §1 (D-1) |
| 4 | GPA threshold value to be confirmed with the mentor | `docs/midterm/RESULTS.md` line 16 ("partly … to be confirmed") |
| 5 | Pipeline of **9** stages (upload; embedded text / OCR; classification; extraction; evidence; auto-acceptance policy; rules; status; review) and the loop back after review | `docs/midterm/ARCHITECTURE_SUMMARY.md` (diagram and stage list 1–9) |
| 5 | **3** statuses; the web app only displays API results | `docs/midterm/ARCHITECTURE_SUMMARY.md` stage 8 and intro; `evaluation/phase_e2/PHASE_E2_REPORT.md` §3 |
| 5 | Stack: Next.js · FastAPI · SQLAlchemy (PostgreSQL schema) · PaddleOCR | `README.md` "Tech Stack" |
| 6 | Status meanings and precedence 보완 필요 > 확인 필요 > 제출 가능; missing required document outranks the rest | `docs/midterm/ARCHITECTURE_SUMMARY.md` stage 8; `evaluation/phase_d2/B2_D2_dev_report.md` (statuses) |
| 6 | Examples: D1 정상 제출; D2 expired tax certificate, 유효기간 종료일 **2026. 08. 31.**; D6 scanned, **4** items for a person | `docs/midterm/DEMO_SCRIPT.md` steps 1, 3, 10; `evaluation/phase_e2/PHASE_E2_REPORT.md` §2; screenshots `docs/midterm/screenshots_v2/after/1280x720/D1_workspace.png`, `D2_workspace.png`, `D6_workspace.png` |
| 7 | Auto-accept only with independent confirmation (another document, application value, check-digit numbers); dates, GPA, student number never confirmed by a second read alone | `evaluation/phase_d/PHASE_D_REPORT.md` §4; `evaluation/phase_d2/PHASE_D2_REPORT.md` §11 (policy change) |
| 7 | Insufficient evidence → 확인 필요; unread required fields to a person; values near a decision boundary to a person | `docs/midterm/ARCHITECTURE_SUMMARY.md` stages 5–6; `evaluation/phase_d2/PHASE_D2_REPORT.md` §4 (D2-2 boundary rule) |
| 7 | Look-alike (지방세) not classified, held for review, never corroborates another document | `evaluation/phase_d2/PHASE_D2_REPORT.md` §4 (D2-1 title gate); `evaluation/phase_d2/B2_D2_dev_report.md` §1 (B11 rows) |
| 7 | "0건" false 제출 가능 (forward reference to slide 9) | see slide 9 |
| 8 | **299** files in the development set; fictional, built on **7** real layouts | `evaluation/datasets/synthetic/test_variants/README.md` lines 3 and 6 |
| 8 | **279** files in each hold-out set (new values, layout jitter, overlapping stamps) | `evaluation/datasets/synthetic/holdout/README.md` lines 8–20; `…/holdout2/README.md` line 20 |
| 8 | Frozen scorer (scorer v2) | `evaluation/phase_d/PHASE_D_REPORT.md` §2; `evaluation/phase_d2/PHASE_D2_REPORT.md` §2 |
| 8 | Injected OCR errors **E1–E12** | `evaluation/phase_d2/PHASE_D2_REPORT.md` §5 (E1–E12) |
| 8 | Hold-out judged once; hold-out 1 became development data afterwards; hold-out 2 judged once | `evaluation/phase_d2/PHASE_D2_REPORT.md` §1 (D-2, D-3), §6; `docs/midterm/RESULTS.md` lines 8 and 51 |
| 8 | Overfitting search: **75** values, **0** hits | `evaluation/phase_d2/PHASE_D2_REPORT.md` §7 |
| 8 | Defects found by the independent audit were fixed and measured before/after | `evaluation/reports/PHASE_B_REPORT.md` title and §"Each fix" |
| 9 | Digital extraction **240/240** (development), **275/275** (hold-out 1), **275/275** (hold-out 2, judged once) → 100 % | `docs/midterm/RESULTS.md` line 34; `evaluation/phase_d2/B2_D2_dev_report.md` §3; `evaluation/phase_d2/PHASE_D2_REPORT.md` §6 |
| 9 | **0** false 제출 가능 (development, hold-out 2 judged once, injected errors); **0** wrongly auto-accepted values; injected cases **474** (development) and **666** (hold-out 1) | `docs/midterm/RESULTS.md` lines 25–29; `evaluation/phase_d2/B2_D2_inj_dev.md` line 4 and totals; `evaluation/phase_d2/B2_D2_inj_holdout.md` line 4 and totals |
| 9 | Review fields per scanned submission: baseline **11.64 / 11.64**; Phase D **3.82 / 3.55**; D2 final **7.23 / 6.59** (scanned PDF / photo images, development set) | `docs/midterm/metrics.csv` (rows B0 baseline, D (S7 before D2), D2 final); `evaluation/phase_d/PHASE_D_REPORT.md` §3, §4 (S7 row); `evaluation/phase_d2/PHASE_D2_REPORT.md` §11 table |
| 9 | **38–43 %** fewer manual checks on scans (−38 % scanned / −43 % photos) | `evaluation/phase_d2/PHASE_D2_REPORT.md` §11 table; `docs/midterm/RESULTS.md` line 43 |
| 9 | The safety rules were tightened after Phase D, which raised the number; accepted by the owner | `evaluation/phase_d2/PHASE_D2_REPORT.md` §11 ("Owner decisions recorded") |
| 10 | hold-out 1 digital extraction **174/275 (63 %)** | `evaluation/phase_d/PHASE_D_REPORT.md` §8 (line 94) and §9 table |
| 10 | After the fixes **275/275** on hold-out 2 | `evaluation/phase_d2/PHASE_D2_REPORT.md` §6 |
| 10 | **1** false 제출 가능 found by hold-out 1 (B11, photographed 지방세 certificate classified as national tax), fixed by the title gate, now 0 | `evaluation/phase_d/PHASE_D_REPORT.md` §8 (B11/images) and §10; `evaluation/phase_d2/PHASE_D2_REPORT.md` §4 (D2-1) and §6 |
| 10 | Review fields **3.82 → 7.23** after the safety rules (title gate, boundary margins, second-pass limit) | `evaluation/phase_d/PHASE_D_REPORT.md` §4; `evaluation/phase_d2/PHASE_D2_REPORT.md` §4 and §11 |
| 11 | Scenarios D1, D2, D5, D6 and their purpose | `docs/midterm/DEMO_SCRIPT.md` steps 1, 3, 6, 10–11; `scripts/demo_scenarios.py` |
| 11 | D6: **4** items confirmed → 제출 가능 automatically; D5 확인 필요 | `docs/midterm/DEMO_SCRIPT.md` steps 6, 10–11; `evaluation/phase_e/PHASE_E_REPORT.md` §3 table |
| 11 (notes) | `make demo-reset` (about **2** minutes), `make demo`, `make demo-rehearsal`, `make demo-stop`; date 2026-10-05 not to be changed; live scan ≈ **15** s per page, digital under a second; fallback tag `midterm-demo-2026-10-14` | `docs/midterm/DEMO_SCRIPT.md` "To show the review again", "Live upload notes", "If something goes wrong"; `README.md` "Demo" |
| 12 | Documents are fictional, real-document pilot is next | `docs/midterm/RESULTS.md` line 49; `docs/midterm/ROADMAP.md` |
| 12 | One rare correlated OCR case auto-accepted in the newest stress test (D3 extended suite, case E3c-both), **0** false 제출 가능 | `docs/midterm/RESULTS.md` line 50; `phase-d3/internal-automation:evaluation/phase_d3/D3_configs.md` (injection table) |
| 12 | hold-out 3 not yet judged | `docs/midterm/RESULTS.md` line 51 |
| 12 | SQLite only, no login; admin screen empty placeholder | `docs/midterm/RESULTS.md` line 52; `evaluation/phase_e/PHASE_E_REPORT.md` §5 items 6–7 |
| 12 | Scan ≈ **16** s per page | `docs/midterm/RESULTS.md` line 53 |
| 13 | November: finish D3 and judge on hold-out 3; reviewer queue; admin checklist screen; real-document pilot (read-only, counts only); PostgreSQL and concurrency | `docs/midterm/ROADMAP.md` "By the November presentation" |
| 13 | December: login and per-project access, privacy (logs, retention), audit log, optional National Tax Service API if the mentor agrees, end-to-end tests, deployment | `docs/midterm/ROADMAP.md` "By December" |
| 13 | **진행 중 (unmerged)**: D3 on development data, decision-blocking review fields per scanned submission **5.41 → 2.68** | `docs/midterm/RESULTS.md` lines 44–46; `docs/midterm/ROADMAP.md` line 6; `phase-d3/internal-automation:evaluation/phase_d3/D3_configs.md` |
| 13 | Merge only after the acceptance table passes with 0 false 제출 가능 | `docs/midterm/ROADMAP.md` line 6 |
| 14 | Q&A talking points (real documents, scan accuracy, privacy, wrong AI) | slides 9, 12, 13 above |
| Notes, all | Target times per slide: 0:30, 0:45, 0:45, 0:45, 1:00, 0:45, 1:00, 1:00, 1:15, 0:45, 0:45, 0:45 = **10:00** (demo and Q&A excluded) | deck planning (the brief asks for ≈ 10 minutes) |

## Tokens the automatic check flags only because of formatting
| Token | Where | Explanation |
|---|---|---|
| `21` | slide 1 | part of the organisation name 플래시21 (from the deck brief) |
| `100.0` | slide 9 chart data | the chart value for 100 % (240/240 and 275/275), same row as the 100 % claim above |
| `3.82/3.55` | slide 9 notes | written `3.82 / 3.55` in the table row for Phase D |
| `4/4` | slide 11 notes | the progress "4 / 4 완료" in `docs/midterm/DEMO_SCRIPT.md` step 11 |

## Left out on purpose
- No number for the size of the hold-out 3 results (not judged), no D3 false-READY figures on any slide except the roadmap note, no estimated or rounded claims such as "halved".
- No contact details or repository link (the repository is private).

## Automated check
`slides_sources.md` is compared with every number in the slide text and speaker notes by the build script's check (run on 2026-10-10): every numeric token in the deck appears in this table, is a slide number, a date, or a time budget listed above. Result (2026-10-10): every numeric token of 2 digits or more, and every decimal, in the slide text, table cells, chart data and speaker notes traced to a row above; the four formatting-only tokens are listed in the previous section.
