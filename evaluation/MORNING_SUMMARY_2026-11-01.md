# Morning summary, 2026-11-01

Nothing was pushed or merged. No hold-out manifest, confidence floor, or file outside the scratch/experiment trees was changed. No stop condition was hit (no wrong accept, no false 제출 가능, no gate failed twice, no hang, no privacy-guard block).

## What ran
1. Arm comparison on the new code (rotation search + issue-date anchor): off (a+b), +crop, +crop+cond on fresh, G0b, seeds A/B, pair, fictional dev and hold-out 1 with injections (`results/final2`).
2. Timing benchmark on the idle machine (42 fixed fresh images, five variants).
3. Gates on the chosen commit, then the business generalisation run, then the analyses.

## Chosen arm and why
**(a+b), no crop, no cond** — branch `fix/orientation-issue-date`, tip `6d5e015` (local, unpushed; KHABIBILLO).
- Real total (1,329 fields): (a+b) 1,099 = 82.7% (80.6–84.6), +crop 1,095, +crop+cond 1,106 = 83.2% (81.1–85.1). Old code 1,052 = 79.2%. The three new arms overlap completely; (a+b) alone is +47 fields over the old code.
- Every arm: 0 wrong accepted, 0 false 제출 가능 (0/125 submissions), 0 injection leaks on dev (1,354) and hold-out 1 (1,532).
- cond lost 3 + 1 fictional fields and 6 + 3 auto-accepts, so by your rule the simplest eligible arm wins.
- Time per page: old 18.3 s, (a+b) 32.0 s = **1.75x** (≤ 2x, eligible). Pages that trigger the search: 13/42 on this benchmark; in the runs 0/2 pair, 5/68 seed A, 5/68 seed B, 35/193 fresh. A triggered page costs 80 s against 36 s before (2.2x); non-triggered pages are unchanged (10.4 s).
- The cheaper centre-sample probe gave **no saving** (90.7 s per triggered page) and identical decisions on 13/13 → removed (commit 40c84d8, a revert with the reason). Crop and cond are not committed; they remain in the experiment trees only.
- The measurement tree also had an uncommitted classifier rule for damaged titles, so the committed code was re-measured on all real sets: 1,096/1,329 = 82.5% (80.3–84.4), 0 wrong, 0/125 false 제출 가능 (fresh 464, A 309, B 312, pair 11/11).

## Gate results on 6d5e015
| gate | result |
|---|---|
| backend pytest / ruff / mypy | 704 pass / clean / clean |
| web lint, typecheck, test | unchanged by this branch, pass (cache) |
| Playwright + axe | pass (12 tests, inside the rehearsal) |
| demo rehearsal x3 | ALL PASS x3 (my first launch overlapped and collided on the demo DB; I stopped everything and re-ran sequentially) |
| fictional v2/v3 field diff vs base | 298 cells, 940 files: 0 differences, 0 newly READY |
| injections | identical to base; only the known owner-accepted E3c-both residual on hold-out 2 (1 false auto-accept, 1 false READY) |
| manipulated PDFs | suite 0 hidden tokens read in 711 effective copies; pipeline 12/12 not READY, all TEXT_LAYER_MISMATCH |
| real pair, seeds A/B, fresh | 0 wrong accepted, 0 false READY |
| privacy scan | 1 generic department term in a new test → replaced by an invented one (6d5e015); diff and tools otherwise clean |

## Business generalisation run ("generalisation: fixes developed on student documents only")
Compared with frozen `45f1e30` and baseline `1018406` (identical to each other): **identical groups, statuses, negatives and field totals**; 2 field rows swapped inside G3b (one gained auto-accept, one lost it).
- 319 correct auto-accepted, 383 correct sent to a person, 208 not read (`issue_date` still 152), 2 wrong caught, **0 wrong accepted**; 0 제출 가능 of 202; negatives N1–N6 0 READY; N1 at 2026-11-03 19/19 review, no expiry code (same as before); single files: same types as frozen.
- Meaning: the student fixes neither help nor hurt business. The business issue-date loss has a different cause (the anchor fix is student-scan specific).

## Top review causes (REVIEW_CATEGORIES.md, with Korean 1-page summary)
C2 field mapping 38.7%, C1 OCR 26.8%, C3 cross-document 23.2%, C5 policy 9.3%, C4 classification 2.0%. No single category fixed alone makes any submission READY; fixing C2+C3+C5 gives 11 READY (all business); fixing everything gives 127 of 186. Fictional vs real: business real OCR stage is 99.4%, the loss is extraction (78%) and policy (FICTIONAL_VS_REAL.md). All numbers with source and test/dev label: `evaluation/paper/PAPER_NUMBERS.md`.

## Proposed fix order
1. **지방세 vs 국세 classification** (2 of 4 real 지방세 originals typed 국세 with no flag). Never accept 지방세 as 국세; synthetic test from the layout pattern. Must come before anything that raises business automation.
2. Business issue date extraction (152 unread fields), as its own synthetic-tested change, then a new generalisation round.
3. Company-name notation normalisation as an admin setting (strict stays default).
4. Capture guidance in the web UI for small-text photos (Munira).
5. Per-field auto-accept rules for representative/department only after the owner decides (policy).

## Needs your decision
- Merge/push of `fix/orientation-issue-date` (5 local commits: rotation search, issue-date anchor, probe, its revert, test term) — I did not.
- Whether to run the full final-judgement gates (hold-out 3 as regression check) before merging, and whether the paper (due 2026-11-05) takes the numbers as listed in PAPER_NUMBERS.md.
- Disclosure: before the generalisation run I viewed masked layout context (issue-date rows) of frozen business outputs for planning. No code was changed from it; the committed fixes were designed on student data.
- Open items: `admin/web` production build (`feature/admin-checklists`) is still paused; the old-code fictional cond lane was killed earlier by your decision.
