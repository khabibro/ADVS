# Automation loop: summary (masked)

Branch `auto/real-automation` (local, not pushed, not merged). Counts and categories only; no document values.
Development data: student fresh G0–G5 + G0b, seed A, real pair; business company F21. Validation (aggregate numbers only): student seed B; business company RS. Validation is a check against overfitting, not an independent test.

## Result in one paragraph

Business: 47 of 76 valid submissions are 제출 가능 at the realistic check date, all correct (unchanged since the validity-end merge); 0 wrong 제출 가능, 0 wrong values confirmed. Student: still 0, but the work behind it is now concrete. Your corrections are in: 학번 is not required on the 재학증명서 (the student is identified by name and date of birth, 학번 is an observation), the certificate-number year anchors the transcript's issue date, and the leak mechanism of the name veto is understood. What is left for the first student 제출 가능 is **not code any more**: the 재학증명서 issue date (90-day rule, cannot be made digit-robust), the university and student name on the 재학증명서 (stamped-line re-read), and GPA (edited-GPA negatives block any robust shortcut). The head is **gate-complete and ready to merge to main** on your word (section "Merge readiness").

## Scoreboard

Correct 제출 가능 = a valid submission on the reduced checklist that is READY with every decision field correct against gold.

| family | start (d9c6c2b) | loop head (e2f56ba) |
|---|---|---|
| student dev (81) | 0 | 0 |
| student validation (27) | 0 | 0 |
| business dev F21, original / realistic date (38) | 0 / 0 | 0 / 24 |
| business validation RS, original / realistic date (38) | 0 / 0 | 11 / 23 |
| wrong 제출 가능, wrong values confirmed | 0, 0 | 0, 0 |
| issues per valid business submission | 6.90 | 1.26 (realistic) |
| auto-accepted correct business fields, dev / validation | 110 / 209 | 211 / 223 before the merge; 279 / 275 after it (realistic dates) |

Negatives: N1, N2, N3, N4, N6 never READY (N3 and N4 also at realistic dates); student negatives 14 of 14 non-READY. **N5 (duplicate upload):** the system ignores the second copy and says so (`DUPLICATE_UPLOAD_IGNORED`), so an N5 submission has the status of its valid counterpart: 12 of 19 are READY at realistic dates, each with that notice and a READY counterpart. That is the existing design; whether a duplicate should block READY is your call (proposal 5).

## Accepted changes (each with synthetic tests)

1. **지방세 vs 국세** decided by issuer words; all 4 real look-alike originals now go to review (2 had been typed national without a flag).
2. **Company-name notation** shared by the acceptance policy and the submission rule (`company_names.py`): parenthesised Latin text, a shorter workplace name under the same valid business number.
3. **Business number** from the one valid hyphenated number when the label does not link.
4. **Proposal 0 (validity end), merged under your conditions a–e:**
   - the other bare dates printed on the page bound the plausible readings of a validity end; default strategy S9;
   - (a) robust-accepted values carry `confirmation = DECISION_ROBUST` and the label "decision-robust (value not individually confirmed)" (+ Korean copy) in the data, never stored or exported as confirmed (UI copy is for the web work);
   - (b) robustness is recomputed for every check date (test and real runs);
   - (c) the 5 hold-out 1 E14 READY cases: fictional check date in mid-October, true validity end 26 days later, injected variant 20–21 days after the check date; true and injected values give the same verdict (valid), and the control run is READY too, so no wrong verdict; metrics now separate `wrong_confirmed`, `robust_wrong` and `false_ready_decision`;
   - (d) new E19 cases (digit errors that cross the validity end, both directions, both passes agreeing): 876 cases, 0 READY, 0 `robust_wrong`, 0 `false_ready_decision`;
   - (e) backend 731 tests, ruff, mypy; demo rehearsal ×3 ALL PASS; manipulated PDFs 0 hidden tokens read; real negatives as above.
   - Injection before / after (four fictional corpora, 6,803 cases): `wrong_confirmed` 1 (the known owner-accepted E3c-both case on hold-out 2), `robust_wrong` 41 (30 on hold-out 1, 11 on hold-out 3, all with the correct verdict), `false_ready_decision` 1 (the same known case).
5. **Student identity and student number (owner correction, 1668443):** no 학번 requirement on the 재학증명서; identity = name AND date of birth (new `birth_date` field on both student document types); 학번 only compared when both documents print it; the transcript's 학번 is also read when its label is split into stacked fragments (it was in the OCR text in 92 of 93 cases that showed no value). Correctly read fields +51 / +10 / +8 (fresh / seed A / seed B), 0 wrong accepted. Tests: same name + same birth date match; same name + different birth date NEEDS_CORRECTION (REVIEW when one side is unreliable); name or birth date on one side only REVIEW; two different certificates of one type go to review (none picked); an identical upload is ignored with a notice.
6. **Year-anchored transcript issue date (cbb5047, your decision 1):** the year that starts the certificate number anchors an inferred issue date; accepted for the decision only when the date carries that year, stands alone in its block, is not near the age limit and is digit-robust; labelled "decision-robust (value not individually confirmed)". Transcript issue dates auto-accepted 2 to 112; correct auto-accepted fields +31 / +24 / +24 / +1; 0 wrong.
7. Harness (no application code): persistent OCR cache for the real runner, cache loader restores `bridge_exempt`, scoreboard, realistic-date submissions (valid + N3/N4/N5), leak separation and E19 in the injection suite.

## Not merged (reverted, with reasons)

- **Name veto on a misread-shaped contradiction** (`proposal/name-veto-variants`): +49 auto-accepted student fields, one new wrong value on hold-out 3. **Mechanism found:** the injection puts the same wrong name on both certificates; the enrolment copy stays vetoed by its own re-read, but the transcript copy (jumbled re-read, no veto) was accepted with that equally wrong, vetoed value as its corroborator. Tightened version (a jumble lifts the veto only if another document carries the same value and its own re-read shows the name) closes it by construction but frees only +2 / +1 / 0 / 0 fields, because the other document's re-read almost never shows the university name (stamped issuer line). Reverted; the cheap fix is to read the issuer line with a region that excludes the date row, which is region sizing, not policy.
- **Decision-robust GPA on the printed shape:** the only reading of a typical GPA that crosses the 3.0 threshold is a dropped leading digit, which cannot be printed; excluding it makes every 3.00–3.99 value robust (+28 / +27 / +7 fields) but an edited-GPA negative on each seed set was then auto-accepted (value differs from gold; its arithmetic is not evaluable, which the robust path bypasses). Hard gate (0 wrong values auto-accepted): reverted before any gate.
- Second-pass region = union of boxes (+2 fields), fragment-aware veto (no gain): reverted earlier.

## What blocks the first correct student 제출 가능 (head)

Issues per valid student submission 8.5 to 6.45; no student submission is complete. Remaining, by size: (1) 재학증명서 issue date (378): the 90-day rule flips under every digit-confusion reading (0 of 130 robust) and it has no second source: needs your decision (proposal 8). (2) 재학증명서 university name (209) and student name (102): second-pass veto on the stamped issuer line and the small header. (3) Transcript GPA (74): no evaluable arithmetic on the page, near the threshold (26), or arithmetic mismatch (22). (4) Transcript student name (32), classification (26 need review).

## Merge readiness (head cbb5047 + tests + docs)

- Backend 755 tests, ruff, mypy `--explicit-package-bases` clean.
- Injection replay, four fictional corpora, 6,813 cases: `wrong_confirmed` 1 (the known E3c-both case on hold-out 2), `robust_wrong` 41 (correct verdicts), `false_ready_decision` 1 (same known case); E19 876 cases 0 READY. Identical to the previously gated head.
- Fictional v3 field diff against the previous head: the new `birth_date` field and the student numbers now read on three scanned sets; **4 status changes READY to REVIEW_REQUIRED, all the fictional S10 digital set** (its transcript prints a masked resident number instead of a date of birth, so the birth date exists on one side only: the rule you set). 0 newly READY. Manifests untouched. This is the one behaviour change you should look at before merging (proposal 9).
- Demo rehearsal x3 ALL PASS (same timings, no hang), Playwright/axe 22 passed, manipulated PDFs 0 hidden tokens read (4 manipulations x 237 copies).
- Real: 0 wrong values accepted, 0 false READY on student and business; business 47 of 76 READY all correct; student negatives 14 of 14 non-READY; business N1–N4, N6 never READY; N5 duplicates READY with the notice (as designed).
- Privacy: one commit was blocked by the guard (an invented test birth date equalled a real one I had seen in OCR output); never committed, replaced, all new test files re-scanned. Docs scanned for gold values.

## Owner decisions needed

5. Done: an identical duplicate stays "ignored with a notice"; different certificates of one type go to review (test added).
8. **Enrolment certificate issue date**: staff one-click date confirmation (recommended; it is a single field and unblocks the 90-day rule), or another independent source. Without it no student submission can be READY.
9. **Fictional S10 / transcripts without a 생년월일**: accept the review outcome, or derive the birth date from a resident-number prefix (sensitive, century ambiguity; not recommended).
10. **University / name on the 재학증명서**: allow me to size the second-pass region of the issuer line to exclude the date row (code only, no policy change), then re-run.
11. Applicant company name (S5+): logged for the admin/web work.

## 요약 (멘토용)

- **결과**: 사업자 서류는 현실적인 점검일 기준 76건 중 47건이 제출 가능(모두 정답)이며, 잘못된 값 확정과 잘못된 제출 가능은 0건입니다. 학생 서류는 아직 제출 가능 0건입니다.
- **소유자 결정 반영**: 재학증명서에는 학번이 인쇄되지 않으므로 학번 요구 조건을 제거하고, 학생 동일성은 이름과 생년월일로 확인합니다(학번은 두 서류에 모두 있을 때만 비교). 성적증명서의 학번은 라벨이 분리되어 놓치던 경우를 읽도록 고쳐 읽힌 필드가 크게 늘었습니다(+51/+10/+8).
- **발급일**: 문서번호의 연도(제 YYYY-…호)를 기준으로 성적증명서 발급일을 결정 기준으로 확인(개별 확인되지 않음 표시)합니다. 재학증명서 발급일은 90일 규칙 때문에 자동 확인이 불가능해 직원 확인 또는 다른 근거가 필요합니다.
- **되돌린 것**: 학교명 검증 완화(원인은 규명했으나 효과 +2건), GPA 결정 기준 확인(조작된 GPA 음성 사례를 통과시켜 안전 기준 위반).
- **안전**: 잘못된 값 확정 0(알려진 1건 제외), 주입 시험 6,813건 이전과 동일, 시연 리허설 3회·Playwright/접근성 시험 통과. 가상 데이터 S10 4건은 생년월일 규칙 때문에 제출 가능에서 검토로 바뀝니다.
