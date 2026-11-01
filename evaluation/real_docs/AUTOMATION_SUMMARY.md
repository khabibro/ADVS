# Automation loop: summary (masked)

Branch `auto/real-automation` (local, not pushed, not merged), 15 commits (including this one) from the gated tip `d9c6c2b`; head is the commit that carries this file. Counts and categories only.
Development data: student fresh G0–G5 + G0b, seed A, real pair; business company F21. Validation (aggregate numbers only): student seed B; business company RS. Validation is a check against overfitting, not an independent test.

## Stop reason

Two consecutive cycles without an accepted improvement (cycle 4 rejected by the safety gate, cycle 6 reverted for no gain), and the remaining clusters need your decision (below). No wrong accept or false 제출 가능 remains on the branch.

## Scoreboard: start → loop head

Correct 제출 가능 = a valid submission on the reduced checklist that is READY with every decision field correct against gold.

| family | medium | start | loop head | on the proposal branch (not on the loop branch) |
|---|---|---|---|---|
| student dev (81) | scan + photo | 0 | 0 | 0 |
| student validation (27) | scan + photo | 0 | 0 | 0 |
| business dev F21 (38) | original dates / realistic dates | 0 / 0 | 0 / 0 | 0 / 24 |
| business validation RS (38) | original dates / realistic dates | 0 / 0 | 0 / 0 | 11 / 23 |

Wrong 제출 가능: 0 everywhere. Negatives READY: 0 of 114 business + 14 student (N1 re-run 0 of 20). Original dates sit on the last valid day of the 국세 납세증명서 (a boundary case by construction); realistic dates are 20 days before the earliest printed validity end.

What the loop head did achieve (auto-accepted correct fields / issues per valid business submission):

| business | start | loop head |
|---|---|---|
| auto-accepted correct fields, dev F21 | 110 | 211 (G0 10 → 14, scans 79 → 151, photos 21 → 46) |
| auto-accepted correct fields, validation RS | 209 | 223 (G0 13 → 13, scans 150 → 158, photos 46 → 52) |
| issues per valid submission, dev | 9.24 | 4.71 |
| issues per valid submission, validation | 4.76 | 4.03 |
| wrong values accepted | 0 | 0 |

(Per-medium numbers are field counts over all variants of that company: G0 originals, scan variants G1/G2/G3/G3b/G5, photos G4.)

## Accepted fixes (each with a synthetic test, one commit)

1. **지방세 vs 국세** (a2bb587): decided by issuer words, not only the title. A local-tax marker anywhere makes the file a look-alike (unknown, reviewed); a national certificate must show a national issuer word. All 4 real look-alike originals now go to review (2 were typed national without any flag); 0 national certificates changed.
2. **Company-name notation** (7515f50 + 10acd1d): parenthesised Latin text is not part of the name; a shorter workplace name agrees when it is the start of the registration name and both documents carry the same valid business number. One shared definition (`company_names.py`) is used by the acceptance policy and by the submission rule. The first version fixed only the policy; that moved 30 valid dev submissions to NEEDS_CORRECTION (INFORMATION_MISMATCH), which the status check found, and the second commit removed.
3. **Business number** (when the label does not link): the one hyphenated number on the page that passes the check digit; two different valid numbers or a failing digit stay unresolved.
4. Harness (no application code): `--ocr-cache` for the real-document runner; the replay loader now restores `bridge_exempt` (it changed 18 fresh-set fields before); scoreboard, realistic-date submissions, test names made fictional.

## Rejected / reverted

- **Cycle 4: validity end bounded by the page's printed dates + default S9 — rejected by the safety gate.** Hold-out 1 injection E14 (a digit of the validity end is wrong, both passes agree): 30 false auto-accepts, 5 false READY (previous commit 0 and 0). It is kept on branch `proposal/robust-validity-window`.
- **Cycle 6: fragment-aware name veto — reverted**: +1 field only; the vetoed regions mostly contain other text, not fragments.

## Gates on the loop head (5c4fb75 + docs)

Backend 723 tests, ruff, mypy clean; injections dev 0/0, hold-out 1 0/0, hold-out 2 1/1 (the known owner-accepted E3c-both case), hold-out 3 0/0 (false auto-accept / false READY); v3 scorer false READY and trusted wrong fields empty on all four corpora; fictional field diff against the previous gated commit: 4 fields, 0 status differences, 0 newly READY (the 4 are a recovered business number on a fictional image and the fictional 지방세 look-alike now not extracted); demo rehearsal ×3 ALL PASS (includes 12 Playwright/axe checks); manipulated PDFs: suite 0 hidden tokens in 711 effective copies, pipeline 12 of 12 not READY; privacy scan of the whole branch diff: only enum names matched.

## What still blocks the remaining submissions, by cluster

Business (loop head, about 4.3 issues per valid submission): the validity end of the 국세 and 4대보험 certificates when scanned (needs independent evidence or the decision-robust path, proposal 0), and rotated or low-quality captures (company-name re-read disagrees, confidence under the floor). Student (about 8 issues per valid submission): (a) the anchored issue date on scans is an inference and is never accepted (about 2 per submission); (b) university name vetoed by the second-pass re-read on 127 dev fields (cause not a fragment; the re-read region is mis-sized and contains other text); (c) GPA without independent confirmation, near the threshold, or failing the arithmetic check; (d) names and student number below the confidence floor. Even with (a) solved, 0 student submissions would be complete (simulation), so student READY needs (a)–(d) together.

## Owner-decision proposals (expected gain, risk)

0. **Decision-robust acceptance of the validity end** (`proposal/robust-validity-window`): 47 of 76 valid business submissions READY at realistic dates (24/38 dev, 23/38 validation), all correct, 0 of 114 negatives READY, expired digital 국세 detected (N1: 16 of 20 NEEDS_CORRECTION instead of none). Cost: wrong digits can be accepted when the verdict is unchanged (E14: 30 false auto-accepts, 5 false READY on hold-out 1). Options: reject; accept with a verdict-based leak definition; or require a one-click confirmation of the date before READY (keeps 0 wrong accepted values).
1. Decision-robust acceptance of the anchored scanned issue date (student): removes about 2 of 8 blockers; alone completes none. Risk: which date it is (inference) rather than a digit error.
2. Applicant company name as the independent source (S5+) in the measurement and in production: unmeasured here.
3. Student: second-pass region sizing for the university veto (engineering, no policy change) and GPA confirmation rules: needed for any student READY.

## 요약 (멘토용)

- **결과**: 안전 기준(잘못된 자동 승인 0, 잘못된 제출 가능 0)을 유지한 채, 사업자 서류에서 확인 필요 항목을 줄였습니다. 서류 1건당 확인 항목: 개발용 회사 9.2 → 4.7, 검증용 회사 4.8 → 4.0. 자동 승인된 정확한 항목: 개발 110 → 211, 검증 209 → 223. 제출 가능으로 바뀐 서류는 아직 0건입니다.
- **고친 것 (빈도 순서와 원인 기반)**: ① 지방세/국세 구분(발급기관 표현으로 판단, 4건 모두 확인 필요로 전환) ② 회사명 표기 차이(주식회사/(주), 영문 괄호, 4대보험의 짧은 사업장명) ③ 사업자등록번호 추출(라벨과 값이 떨어진 경우).
- **라벨+위치 기반 매핑**: 사업자등록번호는 라벨 옆 값이 없을 때 "체크디지트를 통과하는 유일한 번호"로 찾습니다.
- **가장 큰 효과를 내는 변경은 보류**: 유효기간 끝 날짜를 문서에 인쇄된 다른 날짜로 범위를 좁혀 자동 승인하면 사업자 서류 76건 중 47건이 제출 가능이 됩니다(오류 0, 부정 사례 114건 모두 제출 불가, 만료 서류도 탐지). 다만 한 자리 숫자가 틀린 값이 승인되는 경우가 주입 시험에서 30건 나와 안전 기준에 걸렸습니다. 별도 브랜치에 보관했으며 결정이 필요합니다.
- **학생 서류**: 제출 가능 0건. 발급일(추정값)·학교명 재확인·GPA 확인이 동시에 풀려야 합니다.
- **불확실한 점**: 검증용 회사는 개발용과 같은 방식으로 개선이 확인되었지만 폭이 작습니다(회사 2곳, 서류 14종).
