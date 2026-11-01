# Automation loop log (masked)

Branch `auto/real-automation` (from `fix/orientation-issue-date`, gated tip). Counts, categories, reason codes and field names only; no document values.
Measurement: `run_real.py --ocr-cache` (OCR read once, replayed afterwards), `loop_score.py` (READY, correct READY, verification issues per valid submission), `review_categories.py`.
Development: student fresh G0–G5, G0b, seed A, real pair; business F21. Validation (aggregate only, failures not read): student seed B; business RS.

## Scoreboard (valid submissions on the reduced checklist that are READY and correct)

Business is reported at two check dates: "original" = the harness date (last valid day of the 국세 납세증명서, a boundary case by construction) and "realistic" (20 days before the earliest printed validity end; see cycle 0). Student numbers did not change in any accepted cycle.

| state | commit | student dev | student validation | business dev F21 orig / realistic | business validation RS orig / realistic | wrong READY | negatives READY (see N5 note) | issues per valid business submission |
|---|---|---|---|---|---|---|---|---|
| start (gated tip) | d9c6c2b | 0 / 81 | 0 / 27 | 0 / 0 of 38 | 0 / 0 of 38 | 0 | 0 of 114 + 14 | 6.90 |
| cycles 1, 2, 3, 5 | 5c4fb75 | 0 / 81 | 0 / 27 | 0 / 0 | 0 / 0 | 0 | 0 | 4.33 |
| **+ proposal 0 merged (loop head)** | e2f56ba | 0 / 81 | 0 / 27 | 0 / 24 | 11 / 23 | 0 | 0 of 102 + N5 duplicates with a notice | 1.26 (realistic) |

Loop head, business: 47 of 76 valid submissions READY at the realistic date, 11 at the original date. N5 (duplicate upload): the system ignores the second copy and says so (`DUPLICATE_UPLOAD_IGNORED`), so an N5 submission has the same status as its valid counterpart; 12 of 19 N5 submissions are READY at realistic dates, each with that notice and each with a READY valid counterpart. N3 (company mismatch) and N4 (지방세 instead of 국세) stay non-READY at realistic dates. This is the designed duplicate handling; whether a duplicate should block READY is an owner decision (proposal 5).

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

## Cycle 4: validity end bounded by the page's other printed dates; default strategy S9 — rejected first, then MERGED under the owner's conditions (see "Proposal 0 merge")
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


## Proposal 0 merge (owner conditions a–e) — ACCEPTED, e2f56ba
- (c) The 5 hold-out 1 E14 READY cases: fictional check date in mid-October, true validity end 26 days later, injected a day-digit variant 20–21 days after the check date. In all 5 the true value and the injected value give the same verdict (not expired) and the control run of the same files is READY too. No wrong verdict, so the one-click confirmation was not needed.
- (a) Robust-accepted values carry `confirmation = DECISION_ROBUST` and the label "decision-robust (value not individually confirmed)" (Korean copy `label_ko`) in the field data (`auto_acceptance`); they are computed on the fly and never stored or exported as confirmed (no export exists). UI copy is for the web work.
- (b) Robustness is recomputed for every check date (test: the same value stops being robust when the date moves next to it; the real runs at the original and realistic dates show it).
- (c, metrics) The injection report now separates `wrong_confirmed` (must be 0), `robust_wrong` and `false_ready_decision` (READY although the true value gives another verdict).
- (d) New injection cases E19: a digit error that crosses the validity end, valid read as expired and the reverse, both passes agreeing: 876 cases on the four fictional corpora, 0 READY, 0 `robust_wrong`, 0 `false_ready_decision`.
- (e) Gates on e2f56ba: backend 731 tests, ruff, mypy; demo rehearsal x3 ALL PASS; manipulated PDFs 0 hidden tokens read; real sets 0 wrong accepted, 0 false READY; real negatives non-READY (N5 note above).
- Before / after on the injection suites (four fictional corpora, 6,803 cases with E19): `wrong_confirmed` 1 (the known owner-accepted E3c-both case on hold-out 2), `robust_wrong` 41 (30 on hold-out 1, 11 on hold-out 3, all with the correct verdict), `false_ready_decision` 1 (the same known case).

## Student cycles after the merge
- Finding: the real 재학증명서 does not print the student number (gold: verified absent), but the student checklist requires it (REQUIRED_FIELD on the enrolment certificate, Phase D2 decision D-1). 93 of 162 development student submissions carry this blocker and it cannot be satisfied by those documents (proposal 4).
- Finding: simulation of the minimal sets: no student submission is complete unless issue date, GPA, university name, student name, enrolment student number and transcript student number are all solved (about 100 of 189 then complete). One fix cannot produce the first student READY.
- Proposal 1 (anchored issue date, decision-robust): measured on the 214 development dates that are anchored inferences, only 3 are decision-robust, because a year or month digit confusion always flips the 90-day verdict and a lone date has no other printed date to bound the year. Not implemented: the gain would be about 1% of the dates for new risk. It needs an anchor for the year first (proposal 1 below).
- Cycle 7, second-pass region = union of the boxes that make up a value: +2 auto-accepted fields. Mechanism found: the university name is read from the stamped issuer line at the bottom of the page; the region re-read there mixes the date row above and the seal, so the re-read says nothing about the name.
- Cycle 8, name veto only on a misread-shaped contradiction (a stretch of Hangul about the name's length agreeing at 60% of positions): student auto-accepted correct fields +49 (fresh), +9 (seed A), +8 (seed B), business +20, issues per student submission 8.5 to 7.6; injection dev, hold-out 1, hold-out 2 unchanged, **hold-out 3: one new wrong value confirmed** (0 before). Reverted (7dccff3, 290e4fc); kept on `proposal/name-veto-variants`. It is the right direction (the veto is the largest single student blocker that is not policy) but needs a tighter rule or the owner's view on the new leak before it can merge.

## Safety gate status (superseded by the merge section above; 5c4fb75 was the earlier head)
- Backend 723 tests, ruff, mypy clean. Real sets: 0 wrong accepted, 0 false READY, all real negatives non-READY (student 14 + business 114).
- Fictional replay (injections dev, hold-outs 1–3): running; result below when finished.

## Observations for the next cycles
- Student: 0 READY. Per valid submission about 8 issues: issue_date and university name on the enrolment certificate, student number unresolved, GPA. The lone scanned issue date is a semantic inference (needs_review) and is excluded from decision-robust acceptance by design (owner decision, see proposal 1).

## Owner-decision proposals

0. **[DECIDED: accepted with conditions a–e, merged, see above]** Decision-robust acceptance of a validity end bounded by the page's printed dates (business). Branch `proposal/robust-validity-window` (2 commits + the shared notation fix). Effect: 47 of 76 valid business submissions READY at the realistic check date (24 of 38 on the development company, 23 of 38 on the validation company), all correct, 0 of 114 negatives READY, and the expired digital 국세 certificate is detected (N1 at the correct date: 16 of 20 NEEDS_CORRECTION instead of 0). Cost: the harness counts 30 false auto-accepts and 5 false READY on hold-out 1 (E14: a digit of the validity end is wrong, the verdict is right). The question for you: is "wrong digit, correct verdict, marked decision-robust" a leak? If yes, drop it; if no, the injection metric needs a verdict-based definition for robust acceptances (a wrong value must flip a verdict to count). A cheap middle path is to show those fields as "decision-robust, please confirm" and let READY require a one-click confirmation of the date, which keeps 0 wrong values accepted.
1. **Decision-robust acceptance for an anchored scanned issue date (student).** The issue date on student scans is found from the certification sentence above and the issuer line below (committed earlier) but stays `needs_review` as an inference, so it can never be accepted, and it is a blocker on every student submission (about 2 per submission). Proposal: allow the decision-robust path for it when the date lies far from the age limit (the policy margin). Expected gain: removes 2 of about 8 blockers per student submission; alone it makes no student submission READY. Risk: a misread date far from the limit leaves the verdict unchanged; a date near the limit still goes to review.
2. **Default strategy S9** is now the default on the loop branch (part of the merged proposal 0).
3. **Applicant company name as an independent source (S5+).** The harness does not supply the project's company name, so this source is never used in the measurements. If real projects always carry it, company fields would be corroborated by the application. Expected gain: unmeasured here.
4. **Student number on the 재학증명서 (checklist).** The seeded student checklist requires 학번 on the enrolment certificate; the real certificate does not print it. Option: require it on at least one document of the submission (the transcript prints it), as the cross-document comparison already does. Expected gain: removes one blocker from 93 of 162 development student submissions; necessary for any student READY. Risk: none for wrong values (a lone transcript number still needs independent confirmation).
5. **Duplicate upload (N5).** A duplicate is ignored with the notice `DUPLICATE_UPLOAD_IGNORED` and the submission keeps the status of its valid counterpart (READY when that is READY). Your plan expected "detected": should a duplicate lower the status to REVIEW_REQUIRED?
6. **Name veto variants** (`proposal/name-veto-variants`): +49 auto-accepted student fields on the fresh set, one new wrong value confirmed on hold-out 3. Needs a tighter rule or your decision on the leak.
7. Applicant company name (S5+): logged for the admin/web work (needs the applicant input form), not now.
