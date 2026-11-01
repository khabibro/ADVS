# Automation loop: summary (masked)

Branch `auto/real-automation` (local, not pushed, not merged). Counts and categories only; no document values.
Development data: student fresh G0–G5 + G0b, seed A, real pair; business company F21. Validation (aggregate numbers only): student seed B; business company RS. Validation is a check against overfitting, not an independent test.

## Result in one paragraph

Business: with your conditions, the validity-end proposal is merged. At the realistic check date **47 of 76 valid business submissions are now 제출 가능, all correct against gold** (24 of 38 on the development company, 23 of 38 on the validation company); at the harness date (the expiry day of the 국세 certificate, a boundary case by construction) 11 of 76. 0 wrong 제출 가능, 0 wrong values confirmed, the expired digital 국세 certificate is now detected (N1: 16 of 20 NEEDS_CORRECTION, was 0). Student: still 0 — the first student READY needs six clusters solved together, two of them need you (below).

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
5. Harness (no application code): persistent OCR cache for the real runner, cache loader restores `bridge_exempt`, scoreboard, realistic-date submissions (valid + N3/N4/N5), leak separation and E19 in the injection suite.

## Not merged

- **Name veto on a misread-shaped contradiction** (`proposal/name-veto-variants`): +49 auto-accepted student fields on the fresh set (+9 seed A, +8 seed B, +20 business), issues per student submission 8.5 to 7.6, injections unchanged on dev, hold-outs 1 and 2, **one new wrong value confirmed on hold-out 3**. Reverted. It addresses the largest student blocker that is not policy.
- Second-pass region = union of the boxes of a value: +2 fields only (the university name is read from the stamped issuer line, whose re-read mixes the date row above and the seal); reverted with the veto change.
- Fragment-aware name veto: no gain, reverted earlier.
- **Proposal 1 (anchored student issue date, decision-robust): not implemented.** Measured on the 214 development dates that are anchored inferences: only 3 are decision-robust, because a year or month digit confusion always flips the 90-day verdict and a lone date has no other printed date to bound the year. The extra conditions you set (only date in the issuance block, far from the limit, other dates stay review) would cut that further. It needs a year anchor first.

## What blocks the first correct student 제출 가능

Simulation over 189 development and validation student submissions: nothing completes until all of these are solved together; then about 100 do.
1. **Issue date** (scan, anchored inference; both documents): 276 + 91 issues.
2. **Student number on the 재학증명서**: the checklist requires it, the real certificate does not print it (gold: verified absent); 93 of 162 development submissions (proposal 4).
3. **University and student name on the 재학증명서**: no independent confirmation (62, 66) after the veto (cycle 8 shows the veto is the cause of most of this; see `proposal/name-veto-variants`).
4. **GPA** (no independent confirmation 41, near the threshold 26, arithmetic mismatch 22, confidence 20).
5. Transcript student number and name below the confidence floor (24, 17).

## Owner decisions needed

4. **Student number requirement**: require 학번 on at least one document of the submission instead of on the 재학증명서. Removes a blocker from 93 of 162 development submissions; necessary for any student READY; no effect on wrong values.
5. **Duplicate upload**: keep "ignored with a notice" (status of the valid counterpart) or lower the status to REVIEW_REQUIRED?
6. **Name veto**: tighter rule or your decision on the single hold-out 3 leak (`proposal/name-veto-variants`).
1. Student issue date: only worth doing with a year anchor; say if you want that explored.
7. Applicant company name (S5+): logged for the admin/web work.

## 요약 (멘토용)

- **결과**: 사업자 서류에서 유효기간 끝 날짜를 문서에 인쇄된 다른 날짜로 범위를 좁혀 확인하는 방식을 승인 조건(값은 "개별 확인되지 않음"으로 표시, 점검일이 바뀌면 다시 계산, 잘못된 값 0건, 만료 경계 오류 시험 876건 모두 통과)과 함께 반영했습니다. 현실적인 점검일 기준 76건 중 47건이 제출 가능이며 모두 정답, 부정 사례는 제출 불가, 만료 서류도 탐지합니다.
- **고친 것 (빈도 순)**: 지방세/국세 구분, 회사명 표기 차이(주식회사/(주), 영문 괄호, 짧은 사업장명), 사업자등록번호 추출(라벨과 값이 떨어진 경우), 유효기간 확인.
- **학생 서류**: 아직 제출 가능 0건. 발급일(추정값), 재학증명서의 학번(실제 서류에 인쇄되지 않음), 학교명·이름 확인, GPA 확인이 동시에 풀려야 합니다. 이 중 학번 요구 조건과 발급일 처리는 결정이 필요합니다.
- **보류**: 두 번째 판독 결과가 학교명을 부정하는 규칙을 완화하면 학생 서류의 자동 확인이 크게 늘지만(+49) 검증 시험에서 잘못된 값 1건이 통과하여 보류했습니다.
- **안전**: 잘못된 값 확정 0, 잘못된 제출 가능 0 (알려진 1건 제외), 중복 업로드는 "무시됨" 안내와 함께 원래 서류와 같은 상태가 됩니다.
