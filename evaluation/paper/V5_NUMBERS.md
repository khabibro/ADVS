# real-docs-v5 numbers (fallback table for the paper; masked, counts only)

Tag `real-docs-v5` (main 3c1f8ab, 2026-11-03). Default strategy S14 (S11 + company identity by numbers + veto lift for a
value another document reads back). Gates on this tree: unit tests 836 passed, ruff, mypy clean, web tests 109 passed,
Playwright 22 passed (axe 0 serious/critical, phone width, projector sizes), rehearsal x3 all scenarios PASS, injection
6815 cases, real lanes, manipulated PDFs.

## Student (108 valid submissions: dev = fresh 54 + seed A 27, validation = seed B 27)

| | start | v4 | v5 |
|---|---|---|---|
| fully automatic (READY) | 0 | 0 | 0 |
| ready after at most 1 click | 0 | 10 | 14 (dev 13 / validation 1) |
| ready after at most 2 clicks | 0 | 10 | 14 |
| open items per valid submission | 8 (loop start) | 4.05 | 4.01 (fresh 3.78, seed A 4.33, seed B 4.15) |

All remaining one-click cases: the transcript GPA (no independent confirmation on the page; the applicant-entered GPA
route comes in v6). Wrong values accepted: 0 on every set; student negatives (14): 0 READY.

## Business (78 valid submissions: dev company F21 38, validation company RS 38 + 2 multi-page never READY)

| | v4 | v5 |
|---|---|---|
| fully automatic, realistic check date (dev / validation) | 23 / 23 | 28 / 26 |
| <= 1 click, realistic date (dev / validation) | 25 / 28 | 30 / 32 |
| fully automatic, harness date (dev / validation) | 0 / 11 | 4 / 14 |
| <= 1 click, harness date (dev / validation) | 23 / 25 | 28 / 29 |
| issues per valid submission (realistic, dev / validation) | 1.18 / 1.29 | 0.66 / 0.82 |
| total READY of 78 / <= 1 click | 46 / 53 | 54 / 62 |

True negatives (N1-N4, N6): 0 READY. N5 (duplicate upload) is reported as "duplicate detected (second copy ignored)":
12 (v4) / 13 (v5, one extra rotated copy) N5 submissions keep the status of their valid counterpart; none of them is a
negative case.

## Safety totals

- Real sets: wrong values auto-accepted 0, false READY 0, on student fresh / seed A / seed B / pair and business F21 / RS.
- Injection (dev + 3 hold-outs, 6815 cases): wrong_confirmed 1 (the known E3c-both case), false_ready_decision 0,
  robust_wrong 148 (decision-robust acceptances whose verdict is correct), E19 876 cases 0 READY.
- Manipulated PDFs: 237 copies per manipulation, hidden tokens in the text the pipeline reads 0, page trusted 0
  (95 percent upper bound for a miss 1.27 percent).

## Fictional status table (v5 code, one submission per set x version, before injections)

| corpus | READY | REVIEW_REQUIRED | NEEDS_CORRECTION | wrong values accepted | false READY |
|---|---|---|---|---|---|
| dev | 9 | 49 | 12 | 0 | 0 |
| hold-out 1 | 8 | 55 | 13 | 0 | 0 |
| hold-out 2 | 8 | 54 | 14 | 0 | 0 |
| hold-out 3 | 7 | 55 | 14 | 0 | 0 |
| total | 32 | 213 | 53 | 0 | 0 |

One conservative mismatch per corpus (S10, a transcript without a 생년월일: held for review, expected READY).
