# Phase D2 report — close the Phase D gaps, re-judge on hold-out set 2

Branch `phase-d/auto-acceptance` (D2 commits on top of Phase D). **Accepted by the owner with one policy change (§11) and merged into main.**

## 1. Decisions applied
D-1 default student workflow gets the 재학증명서 rules (90-day issue-date age, configurable; `student_id` required); I also added, as seed configuration, a student number / student name comparison between 재학증명서 and 성적증명서 (needed so H15 can never be READY). D-2 hold-out set 1 is development data (used freely). D-3 hold-out set 2 was judged once, guarded by `ADVS_FINAL_JUDGEMENT=1`.

## 2. Frozen evaluation target
Scorer v2 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594` and Phase D injection suite `a81e4ef2…484fd` unchanged. New suite `inject_errors_d2.py` (E10 garbled look-alike title, E11 boundary dates, E12 boundary GPA) frozen before any D2 fix: SHA-256 `08229da0419528164cd863a29a449016febe1bae99369d99214130a9e59f3f57`. `score_d2.py` is a thin entry point (adds the new corpora; scorer v2 itself untouched).
**Hold-out exposure:** hold-out set 2 was found on `~/Desktop` / `~/Downloads` and moved into place by hash verification only. I printed the first five lines of its README by mistake while committing it (generic heading text, no documents, no results). Nothing else was read before D2-7; at D2-7 I read the `checklist_condition` strings and then its `fictional_entities` for the overfitting grep.

## 3. B0-D2 (branch head after Phase D, development data = test_variants + hold-out set 1)
Reproduced Phase D's failures: hold-out-1 B11/images READY (look-alike), S02/S09 digital READY, hold-out-1 digital 174/275 (SME 0/56); injections E10 8+4 false READY, E11 4 false READY, E12 6 false auto-accepts (`B0_D2_*`).

## 4. Fixes (each test-first, committed)
| Fix | Cause | Change | Commit |
|---|---|---|---|
| **D2-3 digital extraction by position** | The hold-out layouts draw the colon of "label : value" as a **separate box** (label cell, ":" cell, value cell); the colon box was taken as the value, so SME / enrolment / business-registration labels never reached their values. A second cause: a seal/stamp mark beside the issue date made the date row "not bare". Shuffled text order was *not* the cause on these files, but it is now handled anyway. | `_merge_separator_boxes` folds a lone separator box into its label; `_date_row_text` ignores a stamp-like box to the right of the date; `PdfProcessor` rebuilds reading order from coordinates (`order_lines`). Tests: shuffled text order (5 seeds) and ±2 pt jitter give identical fields; stamp beside date. Hold-out-1 digital 174/275 → **275/275**, test_variants 240/240. | `8de2f1e` |
| **D2-1 title gate** | Auto-acceptance removed the human step that caught a wrong document type; OCR garbled the look-alike qualifier (`지방새`, `지빙세`, `X방세`) so the type became the national-tax certificate. | `classification/title_gate.py`: an OCR-read document must have a clean in-row title (only the boxes *adjacent* to the title count) or two independent identifier signals; a one-confusion near-match of a look-alike qualifier (**explicit** OCR glyph-confusion table, no similarity score) makes it UNKNOWN; an unexplained prefix or an unclean title sets review. A document that is not established never corroborates another. E10: 0 false auto-accept / 0 false READY (dev 24 cases, hold-out-1 24). | `…D2-1` |
| **D2-2 boundary rule** | Second-pass-only values near a decision boundary. | `BOUNDARY_MARGINS` policy table: dates within **N = 10 days** of the reference date / age limit, GPA within **X = 0.5** of the threshold are not auto-accepted when confirmed only by a second pass. Margins and why: `margins.md` (E11 shifts 0–7 days; N=10 is above the largest tested shift and the 8-day maximum of a day-digit confusion; N ≥ 31 would send every 20–30-day-validity certificate to a human). E11/E12: 0 false auto-accept / 0 false READY. | `…D2-2` |
| **D2-4 student workflow** | S02/S09 reached READY. | Seed: ISSUE_DATE_MAX_AGE 90 d (ERROR), REQUIRED_FIELD `student_id`, plus student id/name comparison enrolment↔transcript. S02 NEEDS_CORRECTION, S09 REVIEW_REQUIRED, S01/S10 READY, S08 REVIEW_REQUIRED, H15 never READY (tests + all development sets). **S02/S09 are no longer disputed.** | `…D2-4` |
| **D2-5 common-mode** | A misread repeated in both passes. | Narrow guards: a `valid_until` more than 400 days after the issue date/validity start or before the issue date is not auto-accepted (`MAX_VALIDITY_SPAN_DAYS`), and a cumulative GPA must lie among the transcript's semester GPAs. Residual below. | `…D2-5` |
Other changes found on the way: API-exposed decisions use the verification's evaluation date (they had used the creation date); extraction tolerance for slightly overlapping neighbouring boxes.

## 5. B1-D2 (development data, `B1_D2_*`)
False READY **0**, false auto-accept **0**, WRONG **0** everywhere. Digital 240/240 and 275/275. Review burden per scanned/image submission: Phase D dev 3.82/3.55 → 4.23/3.68; hold-out-1 4.12/3.72 → 4.36/3.96 (slightly higher: boundary scenarios S03/S04/B06, enrolment scans with a misread title, and the corroboration lost with them). Injections E1–E12: **0 false READY in every injection type**; 0 false auto-accepts for E1–E5, E7, E10, E11, E12 and the single-pass E6/E8/E9. **Residual:** the frozen "-both" common-mode variants of E6/E8/E9 still produce 16–17 false auto-accepts (E6 1, E8 10, E9 5–6): the same wrong value read identically by two differently preprocessed passes on a lone date/GPA/student number (all ended REVIEW_REQUIRED/NEEDS_CORRECTION through other fields). Part of the E8 count is an artefact of the suite (its substring edit also rewrites neighbouring semester GPAs, which defeats the semester-range guard).

## 6. Hold-out set 2 — final judgement (run once; aggregates only; `H2_compare.md`, `H2_*_report.md`)
| | B0 (main) | B1 (branch) |
|---|---|---|
| digital fields correct / wrong / unresolved (of 275) | 176 / 1 / 98 | **275 / 0 / 0** |
| digital by type (correct of N) | BR 16/28, SME **0/56**, tax 42/42, social 41/41, enrolment 20/48, transcript 57/60 | **28/28, 56/56, 42/42, 41/41, 48/48, 60/60** |
| scanned correct / wrong / unresolved | 219 / 0 / 56 | 259 / 0 / 16 |
| images | 235 / 2 / 38 | 264 / 0 / 11 |
| OCR fields auto-accepted (scanned / images) | 0 % / 0 % | 64.0 % / 67.3 % (66.9 / 70.2 % with application values) |
| false auto-accept | 0 | 0 |
| review burden per submission (scanned / images) | 11.64 / 11.64 | 4.60 / 4.24 (**−60 % / −64 %**); 4.28 / 3.92 (−63 % / −66 %) with application values |
| auto-decided submissions | 1/25, 1/25 | 3/25, 4/25 |
| false READY | 0 | **0** |
H13 / H14 / H15: NEEDS_CORRECTION (digital), REVIEW_REQUIRED (scanned, images) — never READY. B11, S07: REVIEW_REQUIRED in all versions. S01, S10 digital READY; S02 NEEDS_CORRECTION; S08, S09 REVIEW_REQUIRED. F13: 4/4 flagged; F12 unchanged. Development vs hold-out 2: digital identical (100 %); auto-accept 64–67 % vs 72–76 % (development) — a modest gap, fewer corroborations in the unseen layouts.

## 7. Overfitting grep (dev + hold-out 1 + hold-out 2 values, whole production tree and seed): **0 hits** (75 values).

## 8. Acceptance table
| Criterion | Result |
|---|---|
| False READY (all sets, all injections E1–E12) | **PASS** — 0 |
| False auto-accept (all sets, single-document injections, E10–E12) | **PASS** for E10–E12 and single-pass injections; **residual** for the frozen common-mode "-both" E6/E8/E9 (16–17, §5) |
| Garbled look-alikes (E10, B11/S07 all versions) | **PASS** — never READY |
| Digital extraction hold-out 2 vs development | **PASS** — 275/275 and 240/240; no type below 100 % |
| Shuffled text order identical | **PASS** (tests) |
| Review burden scanned/images vs Phase D hold-out (~65 %) | **FAIL (narrowly)** — −60 % / −64 % default (−63 % / −66 % with application values) vs −65 % / −68 % |
| B01 scanned/images, hold-out 2 | **Missing link named:** scanned — the 사업자등록증 `company_name` was not extracted from the OCR (so company-name corroboration is incomplete); images — the SME `company_name` read at confidence below the 0.90 floor (OCR_UNCERTAIN). Digital B01 READY |
| S01/S10 READY; S02 NEEDS_CORRECTION; S08/S09 REVIEW_REQUIRED (digital) | **PASS** |
| H13/H14/H15 never READY | **PASS** |
| Digital WRONG not higher than B0-D2 | **PASS** (0) |
| Overfitting grep | **PASS** |
| Quality gates | **PASS** — 533 tests, ruff, format, mypy |

**Not merged** because the review-burden row fails and the common-mode residual (E6/E8/E9 "-both") is not closed. Nothing was pushed, tagged or deleted.

## 9. Remaining problems / needs a human
1. Burden: boundary scenarios and misread-title enrolment scans cost about 0.4 fields per submission; OCR extraction of the 사업자등록증 company name and low-confidence names keep B01 scans at REVIEW_REQUIRED. Candidate next step: a small extraction fix for the business-registration name cell on scans, and a decision on whether −60/−64 % is acceptable.
2. Common-mode misreads of a lone date, GPA or student number (same wrong value in both OCR passes) remain auto-acceptable; the check digit does not protect them. Decide whether such fields should be accepted from OCR at all without a corroborating document.
3. Department (`department`) is never auto-accepted (no independent source), so scanned student submissions always need a human for it and for the unlabelled issue date (owner decision: digital only).
4. READY on rows the manifests leave open (S04/S06, B06, B09 digital): configure comparison rules if they should block.
5. Fictional documents only; a real-document check is still recommended before the demo.

## 10. Reproduce
```bash
cd apps/api
# development data (OCR recorded once, then replayed): corpora dev, holdout
.venv312/bin/python ../../evaluation/harness/run_variants.py --corpus dev|holdout --output /tmp/raw.json --ocr-cache <dir> --ocr-mode record|replay
python3 ../../evaluation/harness/score_d2.py --raw /tmp/raw.json --corpus dev|holdout --out-json o.json --out-md o.md
.venv312/bin/python ../../evaluation/harness/inject_errors_d2.py --corpus dev|holdout --ocr-cache <dir> --out /tmp/inj   # E1-E12
# FINAL JUDGEMENT ONLY (hold-out 2, B0 = a worktree of main with the harness copied in):
ADVS_FINAL_JUDGEMENT=1 .venv312/bin/python ../../evaluation/harness/run_variants.py --corpus holdout2 ...
ADVS_FINAL_JUDGEMENT=1 python3 ../../evaluation/harness/score_d2.py --corpus holdout2 ...
```

## 11. Owner acceptance, final policy change and merge

**Owner decisions recorded**
- The review-burden miss on hold-out set 2 (−60 % / −64 % against Phase D's −65 % / −68 %) is **accepted by the owner**: the safety rules (title gate, boundary margins) cost about 5 points.
- Hold-out set 2 is used up and is not run again. **Hold-out exposure note:** I printed the first five lines of its README (generic heading text; no documents, no results) while committing it, before D2-7; everything else was read only at D2-7 (checklist conditions, then `fictional_entities` for the overfitting grep).

**Policy change (more conservative only).** In the auto-acceptance policy table (`FIELD_RULES`, new column `confirm_by_second_pass`), a second OCR pass of the same image may no longer *confirm* `valid_from`, `valid_until`, `issue_date`, `gpa`, `gpa_scale` and `student_id`. They now need another document or the application value. The second pass is still read for them and still vetoes (S6/S7); business numbers (check digit) can still be confirmed by a second pass; nothing else changed. Because no other document or application value exists for dates and GPA, those fields now always go to a human on scans/photos; a student number is auto-accepted only when the enrolment and transcript agree. Tests updated (`tests/test_phase_d_auto_acceptance.py`).

**Re-run on development data only (test_variants + hold-out set 1), injections E1–E12** (`B2_D2_*`):
| | D2 (B1-D2) | final policy (B2-D2) |
|---|---|---|
| false READY (all sets, all injections) | 0 | **0** |
| false auto-accept, all injections incl. common-mode E6/E8/E9 "-both" | 16–17 | **0** |
| review burden per submission, test_variants (scanned / images) | 4.23 / 3.68 | **7.23 / 6.59** (−38 % / −43 % vs 11.64) |
| review burden per submission, hold-out set 1 (scanned / images) | 4.36 / 3.96 | **7.40 / 6.84** (−36 % / −41 %) |
| OCR fields auto-accepted, test_variants (scanned / images) | 163 / 175 of 240 | 97 / 111 |
| auto-decided scanned/image submissions, test_variants | 3 / 5 of 22 | 1 / 1 |
| digital fields correct | 240/240, 275/275 | 240/240, 275/275 |
| S01/S10 digital READY, S02 NEEDS_CORRECTION, S08/S09 REVIEW_REQUIRED, H13–H15 and B11/S07 never READY | yes | yes |
**Burden cost of the policy change: about +3 fields per scanned/photographed submission** (every validity end, issue date and GPA now needs a person; scanned all-valid business sets such as B01 no longer reach READY on their own, they end at REVIEW_REQUIRED for the validity dates). This is a larger cost than the earlier 5 points; it removes the common-mode residual entirely on the injection suite.

**Remaining items for the next phase**
1. Internal-consistency corroboration for the fields that now go to a human: GPA recomputed from the semester GPAs and credits; validity period vs issue date per document type (configurable), so that dates and GPA can be accepted again without a second pass.
2. Scanned 사업자등록증 company-name extraction (the name cell is not extracted from the OCR on scans).
3. The SME company-name confidence (photographed 중소기업확인서 names are read below the 0.90 floor).
4. Department and the unlabelled issue date on scans stay with a human (no independent source).

## 12. Phase D + D2 in one paragraph
Phase D added auto-acceptance of OCR values confirmed by an independent source (another document, the application value, or — for check-digit numbers — a second OCR pass), cutting manual checking by about two thirds with 0 false auto-accepts on the development data and single-document injections. D2 fixed the hold-out findings: digital extraction by position (hold-out digital 63 % → 100 %), the OCR title gate and look-alike near-match (no more READY on a garbled 지방세 certificate), decision-boundary margins, the student workflow rules, and — by owner decision — second-pass-alone confirmation was removed for the decision-driving fields, which closed the common-mode residual at a further burden cost (§11). False READY is 0 on every development, hold-out and injection run.
