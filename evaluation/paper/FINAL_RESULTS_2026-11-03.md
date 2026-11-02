# ADVS final results, 2026-11-03 (masked: counts, categories and field names only)

Final code: `main` at tag **real-docs-v6** (default strategy S17 = S14 + the optional applicant-entered GPA; S14 = S11 +
company identity by numbers + veto lift). Earlier tags: v4 (start of this loop for the table below), v5 (S14 default).
Gates on this exact tree: unit tests 865, ruff, mypy, web tests 111, Playwright 22 passed (axe: 0 serious/critical, phone
width, projector sizes), demo rehearsal x3 all scenarios PASS (D6 included), manipulated PDFs, real lanes, injection suites
(dev + three hold-outs, 6815 cases).

"Start" = the gated tip at the start of the automation loop (student and business READY 0; business issues per valid
submission 6.90 at that time). Student dev = fresh (54) + seed A (27); student validation = seed B (27). Business dev =
company F21 (38 valid), validation = company RS (38 valid), plus 2 multi-page submissions that are never READY; "realistic"
= the check date 20 days before the earliest printed validity end, "harness" = the last valid day of the 국세 납세증명서
(a boundary case by construction).

## 1. Automation: fully automatic (READY) / at most 1 click / at most 2 clicks / open items per valid submission

### Student (108 valid submissions)

| | start | v4 | v5 | final (v6, no applicant GPA typed) | final + applicant-entered GPA (simulation) |
|---|---|---|---|---|---|
| fully automatic, dev (81) | 0 | 0 | 0 | 0 | 15 |
| fully automatic, validation (27) | 0 | 0 | 0 | 0 | 2 |
| <= 1 click, dev | 0 | 10 | 13 | 17 | 17 |
| <= 1 click, validation | 0 | 0 | 1 | 2 | 2 |
| <= 2 clicks, dev | 0 | 10 | 13 | 17 | 22 |
| <= 2 clicks, validation | 0 | 0 | 1 | 2 | 3 |
| open items per valid submission, dev (fresh / seed A) | about 8 | 3.81 / 4.37 | 3.78 / 4.33 | 3.57 / 3.48 | 2.87 / 2.56 |
| open items per valid submission, validation (seed B) | about 8 | 4.19 | 4.15 | 3.37 | 2.44 |

Without a typed GPA, every remaining one-click student submission waits for the transcript GPA (the page offers no
independent confirmation and a decision-robust acceptance is impossible, see section 7). With the optional GPA field
(route B, measured by simulation from the gold values) 17 of 108 are fully automatic (dev 15, validation 2), 0 wrong.

### Business (78 valid submissions; dev F21 / validation RS)

| | start | v4 | v5 | final |
|---|---|---|---|---|
| fully automatic, realistic date (dev / validation) | 0 / 0 | 23 / 23 | 28 / 26 | 28 / 28 |
| <= 1 click, realistic date | 0 / 0 | 25 / 28 | 30 / 32 | 32 / 34 |
| fully automatic, harness date | 0 / 0 | 0 / 11 | 4 / 14 | 4 / 16 |
| <= 1 click, harness date | - | 23 / 25 | 28 / 29 | 28 / 31 |
| open items per valid submission, realistic | 6.90 (all) | 1.18 / 1.29 | 0.66 / 0.82 | 0.55 / 0.71 |
| open items per valid submission, harness | - | 2.87 / 2.18 | 2.34 / 1.71 | 2.24 / 1.61 |
| total READY of 78 / <= 1 click (realistic) | 0 / 0 | 46 / 53 | 54 / 62 | 56 / 66 |

## 2. Safety

- Wrong values auto-accepted and false READY on every real set (student fresh, seed A, seed B, pair; business F21 and RS
  at both dates): **0**.
- True negatives READY: student negatives (14: expired, wrong document in a slot, missing document, mismatched person) **0**;
  business N1-N4 and N6 **0**.
- N5 (the same document uploaded twice) is reported as **"duplicate detected (second copy ignored)"** and is not a negative:
  13 N5 submissions in the realistic run (1 in the harness-date run) keep the status of their valid counterpart; none
  of them is one of the true negatives.
- Injection suites E1-E21, dev + hold-outs 1-3, 6815 cases: wrong_confirmed **1** (the known E3c-both case, hold-out 2),
  false_ready_decision **0**, robust_wrong 148 (decision-robust acceptances of a misread value whose verdict is correct,
  labelled "판정상 안전 (값 미확정)"), E19 (876 cases) **0 READY**, 0 robust wrong, 0 false READY by decision.
  The legacy "false READY" column reads 16 (v5: 2): all are the fictional student set S09 (photo variants now behave like the
  scan variants): the injected student-number change (E9) is not acted on (the number is not required, the effective value
  stays unresolved) and the E21 cases are not exercised; no wrong value is used by any decision.
- Manipulated PDFs (237 copies per manipulation: hidden text, white on white, tiny text, off page): hidden tokens found in the
  text the pipeline reads 0, page still trusted 0 (95 percent upper bound for a miss 1.27 percent).

## 3. Fictional status table (final code, one submission per set x version, before injections)

| corpus | READY | REVIEW_REQUIRED | NEEDS_CORRECTION | wrong values accepted | false READY |
|---|---|---|---|---|---|
| dev | 10 | 48 | 12 | 0 | 0 |
| hold-out 1 | 10 | 53 | 13 | 0 | 0 |
| hold-out 2 | 10 | 52 | 14 | 0 | 0 |
| hold-out 3 | 9 | 53 | 14 | 0 | 0 |
| total (v5: 32 / 213 / 53) | 39 | 206 | 53 | 0 | 0 |

One conservative mismatch per corpus (S10: a transcript without a 생년월일 is held for review, expected READY).

## 4. Review categories (items on valid submissions, all real lanes; start of loop not recorded in this form)

| category | student v4 | student v5 | student final | business v4 | business v5 | business final |
|---|---|---|---|---|---|---|
| C1 OCR recognition | 307 | 293 | 246 | 49 | 28 | 24 |
| C2 field mapping | 62 | 62 | 62 | 249 | 249 | 249 |
| C3 comparison between documents | 198 | 208 | 208 | 5 | 5 | 5 |
| C4 classification | 8 | 8 | 8 | 0 | 0 | 0 |
| C5 safety policy | 101 | 101 | 101 | 56 | 56 | 56 |

(C3 for students rose because fields that were previously blocked earlier now reach the comparison; the number of
submissions needing a person fell.)

## 5. What was accepted in this stretch (mechanism, gain), what was reverted, future work

Accepted and merged:
- **v5**: S14 default. Company identity by numbers (a business registration number read on two documents, equal, valid
  check digit, identifies the company even when the printed names cannot be confirmed) and the second-pass veto lift (a name
  vetoed by a re-read is accepted when another document reads exactly the same and the re-read is not a plain misread).
  Business realistic READY 46 to 54 of 78. 4대보험/중소기업확인서: a validity end is never derived or confirmed from a rule
  (only a printed value, SME as a consistency check); demo scenario D6 and the phone-width list layout fixed.
- **v6 cycle 1**: a below-floor read that the other document confirms by an exact match (the approved S11 variant b) had
  been accepted by the decision layer but never took effect in the effective value (119 student and 7 business fields);
  it now does. Student <= 1 click 14 to 19 of 108, business READY 54 to 56 and <= 1 click 62 to 66, 0 wrong, dev injection clean.
- **v6 route B**: the optional applicant-entered GPA and scale (backend fields, migration, strict parser, specific review
  reason; applicant web field "성적증명서의 평점평균 (선택)", shown only for workflows with a transcript; photo tips under the
  upload zone). Confirms the OCR read only on exact agreement; a one-digit typo goes to review (typo variant: 0 READY, 0 wrong).
  Student fully automatic 0 to 17 of 108 in the simulation.
- Harness only (report-only): GPA-requirement replay, applicant-GPA simulation, injection suites that follow the threshold.

Measured, not enabled (owner decision): **route A** (same-line GPA-to-백분율 relation fitted from the legend and the semester
lines, never the total line; truncation bound 0.01 x |a| plus the rounding of the 백분율): on its own 0 gain, because a
confirmed GPA near the threshold is still held by the policy margin (0.5) and the relation exists on only about 11 of 27
transcript variants. With an opt-in narrow margin (0.05) for page-confirmed GPAs: 4 student submissions fully automatic
(fresh only), 0 wrong. Route A is therefore off; the narrow margin is a policy question.

Reverted: cycle 2, university name from a footnote sentence when the issuer line is unread (zero effect: the footnote on
these transcripts is the self-referential form that names no university).

Future work (expected gain): reading the transcript issuer line on photos where it is missing (53 of 108 valid transcripts
have no university read; up to 8 more submissions one click away); a lower-noise second read of the name line on photos
(about 100 name/university vetoes, most re-reads differ completely, so the gain is uncertain); the narrow margin for
page-confirmed GPAs together with route A (+4 fully automatic on the development photos); 4.5-scale converted transcript
arithmetic to be shown as "could not check" instead of a mismatch (wording only).

## 6. Limitations (stated plainly)

- All real student submissions are variants of **one document pair** (one enrolment certificate and one transcript, plus a
  second transcript of another scale); one real business per development / validation set. Results say how the system
  behaves on these documents, not on other universities' layouts.
- The fresh photos came from **compressed images**; phone photos taken in the application could read differently.
- The <= 1-click student results are **mostly development data** (validation: 2 of 27); the validation set is seed B,
  derived from the same document pair.
- **Route B is measured by simulation** (the typed GPA comes from the gold values); real applicants may type other
  formats or mistakes, which go to review by construction.
- The injection suites per GPA setting (section 7) were run on the development corpus only, not on the three hold-outs.
- The fictional replay and the real lanes use cached OCR: the OCR itself was not re-run in this stretch (PaddleOCR
  PP-OCRv5, traditional OCR only, nothing sent to online services).

## 7. Effect of the GPA requirement (report-only; no product change; stored OCR replayed under other checklist settings)

Student submissions on the final code, GPA rule of the student workflow replaced or removed in the replay. The
decision-robust rule is unchanged (a GPA is accepted without confirmation only if every likely misreading gives the same
verdict). Dev = fresh + seed A (81), validation = seed B (27). All numbers: wrong values accepted 0, false READY 0, student
negatives (14) READY 0.

| GPA requirement | READY dev / val | <= 1 click dev / val | open items per submission dev / val | injection (dev corpus): wrong_confirmed / false_ready_decision / E19 READY |
|---|---|---|---|---|
| none | 17 / 2 | 17 / 2 | 2.57 / 2.44 | 0 / 0 / 0 |
| >= 2.0 | 0 / 0 | 17 / 2 | 3.54 / 3.37 | 0 / 0 / 0 |
| >= 2.5 | 0 / 0 | 17 / 2 | 3.54 / 3.37 | 0 / 0 / 0 |
| >= 3.0 (current) | 0 / 0 | 17 / 2 | 3.54 / 3.37 | 0 / 0 / 0 |
| >= 3.5 | 0 / 0 | 17 / 2 | 3.54 / 3.37 | 0 / 0 / 0 |

Reading: the threshold value does not change the numbers; whether a requirement exists at all does. With any
requirement the GPA stays a click, because a dropped or added digit is a plausible misreading and moves a 3.x value across
every threshold from 2.0 to 3.5 (the alternatives include values far below it), so the decision-robust rule never accepts
a GPA. With no requirement the GPA is not decision-relevant and 19 of 108 become fully automatic. The same threshold
number applies to the 4.3 and the 4.5 scale (the rule compares the printed GPA); the 4.3-scale transcript of this data set
lies below 3.5, so under >= 3.5 its correct final verdict after a person reads the GPA is NEEDS_CORRECTION, which the system
never pre-empts (it stays in review; 0 false READY). Injection: dev corpus per setting 1548-1560 cases (the threshold-aware
suites E8/E12 aim at each setting), 0 wrong_confirmed, 0 false_ready_decision, E19 0 READY at every setting; with no
requirement the legacy "false READY" column reads 24 because an injected wrong GPA no longer changes any verdict.

## 8. 요약 (멘토용, 한국어 5줄)

1. 최종 코드(real-docs-v6)에서 실제 서류 기준 잘못된 값의 자동 승인 0건, 거짓 '제출 가능' 0건이며 실제 부정 사례(만료·다른 서류·누락·불일치)는 모두 제출 가능이 되지 않았습니다.
2. 기업 서류는 78건 중 56건이 사람 없이 '제출 가능', 66건이 확인 1회 이내로 처리되며(시작 시 0건), 제출 건당 확인 항목은 6.9개에서 0.6개로 줄었습니다.
3. 학생 서류는 성적증명서의 평점평균이 마지막 확인 항목이며, 신청자가 평점평균을 입력하면 108건 중 17건이 자동 처리됩니다(시뮬레이션, 오입력은 모두 담당자 확인으로 이동).
4. GPA 요건의 기준값(2.0~3.5)은 결과를 바꾸지 않고, 요건이 있느냐 없느냐만 영향을 줍니다(요건 없음: 19건 자동, 요건 있음: 0건).
5. 한계: 실제 학생 서류는 한 쌍의 문서에서 만든 변형이며 사진은 압축 이미지입니다. 검증 세트의 개선폭은 작고(27건 중 2건), 새 양식에서의 성능은 별도 확인이 필요합니다.
