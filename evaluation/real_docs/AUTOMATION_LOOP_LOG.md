# Automation loop log (masked)

Branch `auto/real-automation` (from `fix/orientation-issue-date`, gated tip). Counts, categories, reason codes and field names only; no document values.
Measurement: `run_real.py --ocr-cache` (OCR read once, replayed afterwards), `loop_score.py` (READY, correct READY, verification issues per valid submission), `review_categories.py`.
Development: student fresh G0–G5, G0b, seed A, real pair; business F21. Validation (aggregate only, failures not read): student seed B; business RS.

## Scoreboard (valid submissions on the reduced checklist that are READY and correct)

Business is reported at two check dates: "original" = the harness date (last valid day of the 국세 납세증명서, a boundary case by construction) and "realistic" (20 days before the earliest printed validity end; see cycle 0). Student numbers did not change in any accepted cycle.

| state | commit | student dev (fresh+A+pair) | student validation (seed B) | business dev F21 orig / realistic | business validation RS orig / realistic | wrong READY | negatives READY | issues per valid business submission |
|---|---|---|---|---|---|---|---|---|
| start (gated tip) | d9c6c2b | 0 / 81 | 0 / 27 | 0 / 0 of 38 | 0 / 0 of 38 | 0 | 0 of 114 + 14 | 6.90 |
| after cycles 1, 2, 3, 5 (**loop head**) | 5c4fb75 | 0 / 81 | 0 / 27 | 0 / 0 | 0 / 0 | 0 | 0 | 4.33 |
| *proposal branch*: + validity window + S9 | `proposal/robust-validity-window` | 0 / 81 | 0 / 27 | 0 / 24 | 11 / 23 | 0 | 0 | 1.26 |

The proposal row is **not** on the loop branch: its safety gate failed (cycle 4). The loop head gains +115 correct auto-accepted business fields (319 to 434), no READY yet.

## Cycle 0: baseline and how the loop is measured

- Valid submissions that are not READY have, on average, 7.65 verification issues (student 8.19, business 6.9). These are the real blockers: only fields a rule uses can block (`used_by_rules`), so decision-relevance already holds; the earlier "8.47 blocking fields" counted every gold field. Business `issue_date` (152 unread) is not used by any business rule and blocks nothing.
- Business dev (F21) valid submissions: 5.3 blocking rule-used fields each. Main reasons: company/workplace name disagrees with another document (86 field cases), `valid_until` near the decision boundary (34) and without independent confirmation (32+), business number unresolved on 13 scans.
- **Test-design observation:** the harness check date of the G0 valid business submissions equals the last valid day of the 국세 납세증명서 (0 days) and is 13 days before the 4대보험 expiry: a boundary case by construction. The realistic run (`make_realistic_business.py`, 20 days before the earliest printed validity end) is reported next to the original.
- Printed dates on the dev company: the 국세 certificate prints its issue date 1–5 days before its validity end and the 4대보험 certificate 13–16 days before; the validation company 28–30 days. A fixed 30-day validity profile therefore cannot be used as evidence (it would fit one company and not the other); cycle 4 uses a window instead.
- Harness: `--ocr-cache` makes a cycle minutes instead of hours. First replay differed from the live run by 18 fields on the fresh set because the cache loader dropped the OCR line flag `bridge_exempt`; fixed (a92db82), the replay now reproduces the gated numbers exactly (464/309/312/11/702).
- Running the three lanes of one cycle in parallel in the same tree gave one document without fields once (a shared-state artefact); lanes now run one after another for the numbers reported.

## Cycle 1: 지방세 vs 국세 (safety prerequisite) — ACCEPTED (a2bb587)
- Mechanism: the look-alike list only fires on the contiguous title; on the real 지방세 certificates the title is not contiguous, so 2 of 4 originals were typed 국세 without a review flag, and the other 2 reached review only through an unrelated code. All four contain the issuer words (지방세, 구청장) and none of the national ones.
- Alternatives: (a) add more title variants (brittle, repeats the original defect); (b) a classifier for the issuer line (heavier); (c) decide by issuer words: a local marker anywhere = look-alike, a national certificate must show 국세 or 세무서. Chosen (c).
- Result: all 4 look-alike originals now UNKNOWN + review (was 2 unflagged); 20 look-alike files in submissions changed, 0 national certificates changed; no status got less strict except N4 on the standard checklist (NEEDS_CORRECTION to REVIEW_REQUIRED because an unclassified file may be the missing document; never READY).
- Test: `test_tax_certificate_issuer_markers.py` (3 of 4 fail without the fix).

## Cycle 2: company-name notation — ACCEPTED after a follow-up fix (7515f50, then the cycle 5 commit)
- Mechanism: the acceptance policy compares names for exact equality after removing the legal form; the registration and tax certificates print a parenthesised Latin text beside the name and the insurance certificate prints a shorter workplace name, so 86 of the dev company's blocked name fields were "disagrees with another document".
- Fix: Latin-only parentheses are not part of the name; a shorter name agrees when it is the start of the longer one and both documents carry the same business number that passes the check digit. Alternatives rejected: edit distance (not allowed), an alias list (needs input from the applicant).
- Result: dev company +88 correct auto-accepted fields, validation company +0 (its names already agreed: the fix is general but only the dev company needed it), 0 wrong accepted.
- **Defect found by this cycle's status check, not by the field counts:** 30 of 38 dev valid submissions moved from REVIEW_REQUIRED to NEEDS_CORRECTION, because the submission rule still compared names strictly and reported INFORMATION_MISMATCH once the value was trusted. Fixed in cycle 5 by one shared definition (`company_names.py`) for both layers. New acceptance criterion from here on: no valid submission may get a stricter status.

## Cycle 3: business number from the one valid hyphenated number — ACCEPTED
- Mechanism: the number was taken only next to its label; a split or parenthesised label (13 dev scans) left it unresolved although the page printed it.
- Fix: if no label links, take the only hyphenated number on the page that passes the check digit (two different valid numbers or a failing digit stay unresolved); it is accepted only through corroboration.
- Result: +27 correct auto-accepted fields, verification issues per valid business submission 5.49 to 4.79, 0 wrong.

## Cycle 4: validity end bounded by the page's other printed dates; default strategy S9 — REJECTED by the safety gate (kept on `proposal/robust-validity-window`)
- Mechanism: a lone scanned validity end can only be accepted for the decision when every plausible misreading gives the same outcome. The year and month digits made that impossible without an issue date, and the issue date is not extracted for these certificates.
- Fix: the other bare dates printed on the page bound the plausible readings (a reading must lie 0–400 days after one of them); the read value must lie in such a window; printed dates are taken as read (one misread box at a time, the module's existing safety argument). The default strategy becomes S9 (decision-robust acceptance, implemented and injection-tested in D3).
- Result: validation company 11 READY at the original date and 23 at the realistic date; N1 (one day after expiry, check date 2026-11-03) now 16 of 20 NEEDS_CORRECTION (was 19 of 19 REVIEW_REQUIRED without an expiry code): the expired digital 국세 certificate is detected.
- **Safety gate: hold-out 1 injection E14 (validity end misread by one digit, both passes agree): 30 false auto-accepts and 5 false READY; the previous commit had 0 and 0** (dev: 0). Examples: a true day digit 7 read as 1 or 2, accepted because the verdict (not expired) is the same. This is the robust path working as designed: the value can be wrong while the decision is right, and the harness counts a wrong accepted value as a leak. Rule: a fix that adds even one is reverted. Reverted (5c4fb75); the change stays on a proposal branch for the owner (proposal 1 below).
- Side effect that is now moot on the loop branch: the verification notation fix (cycle 5) stays, because it removes a false NEEDS_CORRECTION that cycle 2 would otherwise cause.

## Cycle 5: verification uses the same notation logic (shared `company_names.py`) — ACCEPTED
- Result on the loop head: 0 valid submissions with a stricter status (the 2 NEEDS_CORRECTION among "valid" are the two multi-page files, unchanged from the baseline), issues per valid business submission 4.33. On the proposal branch the same commit shows 47 of 76 READY.

## Cycle 6: fragment-aware name veto — REVERTED (cedf6d6)
- Hypothesis: the second-pass university re-read is a one-character fragment of a letter-spaced header, so the veto fires without information (127 dev fields).
- Result: +1 auto-accepted field, 8.50 to 8.48 issues per student submission. The vetoed regions mostly contain other text (digits, Latin), not fragments, so the mechanism covered about 1 of 127 cases. No gain, reverted.

## Safety gate status (loop head 5c4fb75)
- Backend 723 tests, ruff, mypy clean. Real sets: 0 wrong accepted, 0 false READY, all real negatives non-READY (student 14 + business 114).
- Fictional replay (injections dev, hold-outs 1–3): running; result below when finished.

## Observations for the next cycles
- Student: 0 READY. Per valid submission about 8 issues: issue_date and university name on the enrolment certificate, student number unresolved, GPA. The lone scanned issue date is a semantic inference (needs_review) and is excluded from decision-robust acceptance by design (owner decision, see proposal 1).

## Owner-decision proposals

0. **Decision-robust acceptance of a validity end bounded by the page's printed dates (business) — the big one.** Branch `proposal/robust-validity-window` (2 commits + the shared notation fix). Effect: 47 of 76 valid business submissions READY at the realistic check date (24 of 38 on the development company, 23 of 38 on the validation company), all correct, 0 of 114 negatives READY, and the expired digital 국세 certificate is detected (N1 at the correct date: 16 of 20 NEEDS_CORRECTION instead of 0). Cost: the harness counts 30 false auto-accepts and 5 false READY on hold-out 1 (E14: a digit of the validity end is wrong, the verdict is right). The question for you: is "wrong digit, correct verdict, marked decision-robust" a leak? If yes, drop it; if no, the injection metric needs a verdict-based definition for robust acceptances (a wrong value must flip a verdict to count). A cheap middle path is to show those fields as "decision-robust, please confirm" and let READY require a one-click confirmation of the date, which keeps 0 wrong values accepted.
1. **Decision-robust acceptance for an anchored scanned issue date (student).** The issue date on student scans is found from the certification sentence above and the issuer line below (committed earlier) but stays `needs_review` as an inference, so it can never be accepted, and it is a blocker on every student submission (about 2 per submission). Proposal: allow the decision-robust path for it when the date lies far from the age limit (the policy margin). Expected gain: removes 2 of about 8 blockers per student submission; alone it makes no student submission READY. Risk: a misread date far from the limit leaves the verdict unchanged; a date near the limit still goes to review.
2. **Default strategy S9** is part of proposal 0 only; the loop branch keeps S8.
3. **Applicant company name as an independent source (S5+).** The harness does not supply the project's company name, so this source is never used in the measurements. If real projects always carry it, company fields would be corroborated by the application. Expected gain: unmeasured here.
