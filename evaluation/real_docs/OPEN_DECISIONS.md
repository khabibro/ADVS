# Open decisions and plan (masked: no real values, counts only)

Updated 2026-11-02. Re-read this file after any context compaction.

## Standing rules
- Hard gates: 0 wrong values auto-accepted, 0 false 제출 가능. Uncertain goes to a person.
- Privacy: real documents and values only under `data/private_real/` (git-ignored). Reports and committed files hold masked values and counts only. Nothing is sent online.
- Commits: backend/docs as KHABIBILLO via `github-khabibro`; no AI attribution trailers (the hook adds the Munira co-author line).
- Never change hold-out manifests. Never lower confidence floors. The second-pass veto and floor stay unless the owner approves.

## S15 / S14 default conditions
- **S15** (company identity by numbers) becomes the v5 default only if (a) the injection evidence shows no new `wrong_confirmed` / `false_ready_decision` (the known E3c-both case is the only allowed one) and (b) RS validation holds or improves at both the realistic and the harness date.
- **S14** (veto lift) is separate: the default only if every lifted value is independently confirmed by another document; otherwise it stays off.

## SME and 4대보험 printed-end rule
- A validity end derived from a rule is used only as a consistency check, never as the value.
- 4대보험: no derived-validity profile (the real ends are 7–28 days after the number date). The printed end is read; an unread printed end goes to review.
- SME: consistency-only (span 364–365 days). The printed end only.
- NATI keeps its 30-day legal profile. 지방세 is never accepted as 국세 (N4).

## N5 wording
- Duplicates are reported as "duplicate detected (second copy ignored)", not as negatives.
- The true negatives are N1–N4 and N6.

## GPA routes (report-only; the owner decides what goes into the product)
- **A** (S16): the same-line GPA↔백분율 linear relation, fitted from legend pairs plus semester pairs only. **The total line is never in the fit.** At least 3 agreeing pairs. The total line is then checked against the relation. Truncation bound: GPA ∈ [p, p+0.01), so the 백분율 bound is 0.01·|a| plus the 백분율's own rounding. The total line cannot confirm itself (tested).
- **B** (S17): the applicant-entered GPA and scale confirm the read value only on exact equality. A one-digit typo variant goes to review (`CONFLICTS_WITH_APPLICATION_VALUE`).
- **A+B** (S18).
- Report A, B and A+B side by side, dev and validation: GPAs confirmed, READY fully automatic, ≤1 click, wrong = 0. B also measured with the typo variant.
- Withdrawn: the margin-relaxation proposal (my earlier claim about arithmetic confirming 32 near-boundary GPAs was wrong).

## Chain order (one heavy job at a time)
`/tmp/advs-gates/chain_g9.sh`: S15 injection, S15 lanes, S14 injection, S14 lanes. Started 18:27 KST. OCR and injection jobs never overlap. A corpus that aborts is rerun alone before reporting. Only after the chain: the A/B/A+B runs, then the final default gates (UI/rehearsal ×3 with D6, Playwright/axe, manipulated PDFs, real lanes).

## Before any merge
- The full test suite, ruff and mypy pass on the merged result.
- All gates pass on the merged result.
- The fictional status table on the v5 candidate (READY / REVIEW / NEEDS_CORRECTION, wrong values, false READY).
- Merge `--no-ff` (no squash), push and tag `real-docs-v5` via github-khabibro. **No push or merge without passing gates.**
- Remove the temp worktrees (g9 and others) after checking git status.

## Freeze
- Paper freeze: **2026-11-04 09:00 KST**. Whatever is gated and merged by then goes in the paper.
- After v5 is merged and tagged, write the final paper numbers table: business and student, dev/validation, realistic and harness date, the fictional status table on v5, safety totals.
- Also update AUTOMATION_SUMMARY and AUTOMATION_LOOP_LOG (round 7+: 4a business, 4대보험/SME diff, S14/S15, GPA analysis, the withdrawn proposal).
