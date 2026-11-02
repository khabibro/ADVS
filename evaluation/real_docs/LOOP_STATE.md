# LOOP_STATE (masked; counts only). Re-read after any context compaction.

Loop: maximum safe automation, STUDENT FIRST, until 2026-11-03 12:00 KST. Autonomous: no questions; if a case is not
covered take the safer option, log it, continue. Full brief: the owner's 2026-11-03 message (sections 0–6).

## Hard rules
- 0 wrong values auto-accepted and 0 false 제출 가능 on every real set, every true negative (N1–N4, N6, student
  negatives) and the injection suites (only the known E3c-both case). A change that adds one is reverted.
- Never lower floors; no acceptance without independent evidence or decision robustness; no real values or
  institution constants in code; a synthetic test per fix; privacy guard on; real data only in `data/private_real/`.
- One heavy job at a time. Rerun any aborted corpus before reporting.
- Merge only with all gates green: `--no-ff`, no squash, no rewrite. Backend as KHABIBILLO (hook adds Munira); frontend
  with `git -c user.name=Munira -c user.email=munira@knu.ac.kr` plus trailer `Co-authored-by: KHABIBILLO
  <khabibillionaire@gmail.com>`. No AI trailers. Push via `git@github-khabibro:khabibro/ADVS.git`. Never push red main.
  Do not delete branches, tags or worktrees.

## Timeline (KST, 2026-11-03)
- now → ~03:00: default gates on S14 (stacked on S15) as the default, full tests, merge, push, tag `real-docs-v5`,
  write the v5 numbers table immediately.
- ~03:00 → 08:00: improvement cycles, student first. Route A accepted before 05:00 → full gates, merge as v6.
- 08:00 code freeze. 08:00 → 11:00 full gates on the final batch; merge/tag only if green by 11:00, else the last
  green tag is final. 11:00 → 12:00 write `evaluation/paper/FINAL_RESULTS_2026-11-03.md` (+ copy to ~/Desktop), stop.

## Pre-approved
- S14 (includes S15) as the default for v5. GPA route A default if it passes the fast gate; route B for the product
  (backend field + applicant web field, measured by simulation + one-digit typo variant, reported separately and A+B).
- Route A rules: fit only from legend and semester pairs, never the total line; >=3 pairs all within 0.01·|a| + the
  백분율's rounding; total confirmed if its pair fits; no relation -> current behaviour; converted transcripts show
  "검산 불가", never mismatch.
- UI (light work, never blocks automation): applicant GPA field, per-document status sentences, photo tips, 360 px,
  admin Enter-to-confirm, Korean labels. UI joins the final batch only if green by 08:00.
- Stop improving early (still deliver the final results) if a wrong value / false READY appears that a revert does not
  remove, a gate fails twice for the same fix, or a run hangs (> 2x expected time).

## Current step
- [00:55] v5 candidate: route A/B code parked on branch `auto/gpa-routes` (S16–S18, off by default); default S14 set
  on `auto/real-automation`. Evidence for v5 (code identical to the tested S14 runs): injection s14g (6815 cases, 1
  known E3c-both, 0 false_ready_decision), lanes s14g (0 wrong, true negatives 0 READY, N5 duplicates only).
- [00:55] v5 gate chain `/tmp/advs-gates/chain_g10.sh` running in worktree ADVS-g10 (commit 7056398): UI step failed at
  start (git-ignored synthetic test data was missing in the worktree) -> data copied in, UI re-run queued after the
  chain (`chain_g10b.sh`); then lanes (biz/real/student), then the four injection corpora. One heavy job at a time.
- Route B backend done on `auto/gpa-routes` (Project.applicant_gpa/_scale, migration 0007, parser, API, tests; 860+
  tests). Route A/B/A+B harness measurement queued after the v5 chain. UI work for the applicant GPA field next.
