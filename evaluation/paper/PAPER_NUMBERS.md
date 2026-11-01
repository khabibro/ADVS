# Paper numbers: value, source, test or development, denominator

Every number below was produced in this work; the source is a script and a private (git-ignored) or committed result. Real-document sources are under `data/private_real/results/` (not committed). Wilson 95% intervals. "Dev" = development data (used to design fixes), "Test" = not used for tuning, "Gen" = generalisation run (fixes made on student documents only, business never used for code changes).

## A. Real student documents, committed code (`fix/orientation-issue-date`, tip 6d5e015, same code as 393f7bb)
Source: `results/final3/gate/*`, scorer `score_fresh.py`, `score_variants_real.py`, `score_real.py` (via agg3.py).
| set | role | correct / fields | % (Wilson) | wrong accepted | false 제출 가능 | auto-accepted |
|---|---|---|---|---|---|---|
| fresh captures | Dev (since the fixes; was the official test for the frozen commit) | 464/594 | 78.1 (74.6–81.3) | 0 | 0/56 | 53 |
| seed A | Dev | 309/362 | 85.4 (81.3–88.6) | 0 | 0/34 | 28 |
| seed B | Dev | 312/362 | 86.2 (82.3–89.4) | 0 | 0/34 | 25 |
| real pair | Dev | 11/11 | 100 (74.1–100) | 0 | 0/1 | 1 |
| total | Dev | 1,096/1,329 | 82.5 (80.3–84.4) | 0 | 0/125 | 107 |

## B. Same sets before this change (commit 0f35f08 + page-prep tree, no rotation search/anchor), arm "off"
Source: `results/final/off`. Total 1,052/1,329 = 79.2% (76.9–81.3), 0 wrong accepted, 0/125 false 제출 가능, 109 auto-accepted. Dev.
Arms on the old code: crop 1,068 (80.4%), crop+norm:36 1,059 (79.7%), cond 1,077 (81.0%; 78.8–83.1). All within the Wilson overlap.

## C. Arm comparison on the new code (rotation search + issue-date anchor) — `results/final2/*` (measurement tree also contains an uncommitted classifier rule, so the "off" row differs from section A by 3 fields)
| arm | real total | fresh | seed A | seed B | fictional dev | fictional hold-out 1 | injection cases dev / hold-out 1 | auto-accepted |
|---|---|---|---|---|---|---|---|---|
| (a+b) | 1,099/1,329 = 82.7% (80.6–84.6) | 464 | 309 | 315 | 751/753 | 818/825 | 1,354 / 1,532, 0 leaks | 107 |
| (a+b)+crop | 1,095 = 82.4% | 458 | 308 | 318 | 751/753 | 818/825 | 1,354 / 1,532, 0 leaks | 108 |
| (a+b)+crop+cond | 1,106 = 83.2% (81.1–85.1) | 469 | 308 | 318 | 748/753 | 817/825 | 1,350 / 1,530, 0 leaks | 122 |
Chosen: (a+b) (simplest within the Wilson overlap; cond loses 3 and 1 fictional fields and 6/3 auto-accepts). Fictional rows: dev = Dev, hold-out 1 = Test.

## D. Rotation search and timing
Trigger counts (pages searched / pages): pair 0/2, seed A 5/68, seed B 5/68, fresh 35/193 (rotation changed on 28). Source `trigger_stats.py`.
Timing benchmark, 42 fixed fresh images, sequential, idle machine (`bench_all.sh`): old code mean 18.3 s/page; (a+b) 32.0 s/page (1.75x); crop 31.4 s; cond 31.6 s. 29 pages not triggered: 10.3 s old vs 10.4 s new. 13 triggered pages: 36.1 s old vs 80.2 s new (2.2x). Centre-probe variant (fraction 0.6): 90.7 s per triggered page, decisions identical on 13/13 → not adopted, removed.

## E. Fictional documents (replay gates), candidate 393f7bb vs base 0f35f08
298 set/version cells, 940 files, 4 corpora (dev, hold-out 1, hold-out 2, hold-out 3): 0 field differences, 0 status differences, 0 newly 제출 가능. Injection cases: dev 1,354, hold-out 1 1,532, hold-out 2 1,518, hold-out 3 1,527, identical in both commits. Single known residual: 1 false auto-accept and 1 false 제출 가능 on hold-out 2 (E3c-both, owner-accepted, `PHASE_G_REPORT.md`). Hold-out 3 is development data since Phase G; its run is a regression check, not a test.

## F. Manipulated PDFs
Suite (`pdf_manipulation_suite.py`): 237 copies per mode (hidden text, white on white, 0.5 pt text), 0 hidden tokens in the text read, 0 pages still trusted, rule-of-three upper bound 1.27%; off-page text 237 copies, not effective against a plain extractor. Pipeline: 12 manipulated submissions, 0 reached 제출 가능, 12 with TEXT_LAYER_MISMATCH, control READY. Fictional, Test.

## G. Business documents (mentor's files, 2 companies, 14 originals, correlated variants) — Gen
Source `results/final3/biz*`, `score_business.py`. Frozen (45f1e30), baseline and this commit give the same groups and statuses; 2 field rows swapped within G3b.
- 912 scored fields: 319 correct auto-accepted, 383 correct sent to a person, 208 not read (issue_date 152, business number 27, representative 20, workplace 4, company 4, valid-until 1), 2 wrong caught, 0 wrong accepted (rule-of-three bound 0.9% of 319).
- 202 submissions, 0 제출 가능; valid reduced checklist 0/76; negatives N1–N6 114 submissions, 0 제출 가능; N1 at 2026-11-03: 19/19 review, no expiry code; N6: 16/19 expiry.
- G0 original digital: fields 26/32 = 81.3% (64.7–91.1); scan 14/16 = 87.5% (64.0–96.5).
- 지방세 typed as 국세: 19/19 files in submissions; in single files 2 of 4 without a review flag (unchanged by this work).

## H. Review categories (`review_categories.py`, `results/review_categories_final3.json`)
2,615 fields not auto-accepted: C1 701, C2 1,011, C3 607, C4 52, C5 244 (shares 26.8 / 38.7 / 23.2 / 2.0 / 9.3%). 314 submissions, 186 valid not 제출 가능, 0 wrong effective. Student rows Dev, business rows Gen.

## I. Fictional vs real
`FICTIONAL_VS_REAL.md`: OCR-stage 95.8% (94.8–96.6), extraction given text 79.9% (78.1–81.7) over 1,972 real fields; fictional dev 99.7%, hold-out 1 99.2%.

## J. Software gates on the committed code
Backend 704 tests pass; ruff and mypy (`--explicit-package-bases app`, 77 files) clean; web lint/typecheck/test unchanged by this branch (cache hit); demo rehearsal x3 all pass (D1–D9, web, admin, UI: 12 Playwright tests incl. axe); privacy scan of diff and analysis tools against the private gold values: 1 generic term in a test, replaced by an invented one (commit 6d5e015).
