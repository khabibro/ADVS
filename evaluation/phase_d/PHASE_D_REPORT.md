# Phase D report — safe auto-acceptance of OCR values, stress-tested

Branch `phase-d/auto-acceptance`. Not pushed, not merged. Production code was frozen before the hold-out judgement (D6) and not changed afterwards.

## 1. Decisions applied
1. Student issue date: an unlabelled issue date is trusted from **digital text only**, when exactly one date sits between the certification sentence ("…증명합니다") and the issuer line. S08 stays REVIEW_REQUIRED.
2. Scorer v2: NFKC-equivalent text equal (㈜ = (주)), whitespace ignored for names/text; numbers and dates strict.
3. B11/S07: REVIEW_REQUIRED is the accepted design (scorer v2 expects it).
4. B09: duplicate upload may leave the submission READY, but the API response now carries a `notices` entry `DUPLICATE_UPLOAD_IGNORED`.
5. Auto-acceptance approved under the section-4 rules.

## 2. Frozen evaluation target
- Scorer v2 `evaluation/harness/score_v2.py` SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594` (unchanged at every run; rules in its docstring).
- Injection suite `evaluation/harness/inject_errors.py` SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`, seed 20261005 (unchanged). It injects E1–E9 at observation level with confidence 0.95–0.999 into the recorded real OCR; "-both" variants also corrupt the second-pass reading the same way (common-mode worst case). A case counts only if the un-injected control read the field correctly ("exercised").
- Harness: hold-out set refused without `ADVS_FINAL_JUDGEMENT=1`; every hold-out run logged in `holdout_runs.log`.

**Hold-out exposure:** none before D6. The set was found in `~/Downloads` (not inside the repo as the prompt assumed) and moved into place by D0 using only the manifest hashes; no document, result or answer key was read or run before D6. At D6 I read the manifest's top-level entity names (to run the overfitting grep), the `checklist_condition` strings and the titles of H13–H15.

## 3. B0 (main, development set)
Digital 240/240 fields correct; scanned 139 correct / 3 wrong / 98 unresolved; images 199 / 1 / 40; every OCR field goes to a human (auto-accept 0 %); review burden 11.64 fields per scanned/image submission; auto-decided scanned/image submissions 1/22 each (B08 only); false READY 0. Injection suite on B0: 0 false auto-accept, 0 false READY (`B0_injection_*.md`). Files: `B0_report.md`, `B0proj_report.md`.

## 4. Algorithm and strategy comparison
Implemented in `apps/api/app/document_intelligence/auto_acceptance.py` (rule table `FIELD_RULES`, one switch `Settings.auto_accept_strategy`, per-workflow off-switch `auto_accept_disabled_workflows`), wired into the effective-value resolver, so verification, the review queue and the document API all agree. Decisions are computed on the fly from current documents (re-processing invalidates them); machine evidence is never changed; human review is untouched. Rules: exact equality after canonicalisation only; a different file hash or a second pass with different preprocessing (crop + autocontrast + ×1.6) is required; no majority voting; names are never accepted by a second pass; the application value (project company/applicant name) wins and blocks agreeing-but-different documents (H14-type); a failed check digit/format/date logic blocks.

Strategies (S0 none … S7). Development set, all measured on the final code (`strategy_comparison.md`):

| Strategy | auto-accept scanned / images | needs-human fields per submission (scanned / images) | single-doc injection false accept / false READY | correlated (E2/E3/E5/E7-all) false accept / false READY (no application values) | both-passes (common-mode) false accept |
|---|---|---|---|---|---|
| S0 | 0 % / 0 % | 11.64 / 11.64 | 0 / 0 | 0 / 0 | 0 |
| S1 conf only | 81.2 / 83.3 % | 2.77 / 2.55 | **133** / 0 | 42 / 5 | 51 |
| S2 + validators | 52.1 / 52.1 % | 5.95 / 5.95 | **51** / 0 | 0 / 0 | 51 |
| S3 + corroboration | 43.8 / 46.2 % | 6.86 / 6.59 | 0 / 0 | 38 / 0 | 0 |
| S4 + second pass | 71.7 / 74.2 % | 3.82 / 3.55 | 0 / 0 | 38 / **5** | 23 |
| S5 + application values | 71.7 / 74.2 % | 3.82 / 3.55 | 0 / 0 | 38 / **5** | 23 |
| S6 + numeric veto | 71.7 / 74.2 % | 3.82 / 3.55 | 0 / 0 | 38 / **5** | 23 |
| **S7 + name veto (chosen)** | 71.7 / 74.2 % | 3.82 / 3.55 | 0 / 0 | **0 / 0** | 23 |

**Choice: S7.** S3–S7 have 0 false auto-accepts on the development set and on every single-document injection; S4–S7 tie on burden. S5/S6 leave 5 false READY in the all-documents company-name injection when no application value exists (every document carries the same misread name). S7 adds one rule — a second pass may *contradict* a name (never confirm it) — and removes those at identical measured burden. This deviates from "simplest of the close ones": S5 is one config value away if you prefer it. S1 and S2 fail the injection suite, which is why they are shown.

Calibration (`calibration_table.md`): on the development set no confidence level separates correct from wrong OCR values (the only wrong values, glued departments, sit at 0.98–0.995) and the injection suite deliberately uses 0.95–0.999, so confidence is only a floor (0.90, the existing policy minimum), never a reason to accept.

## 5. Injection results (development set, S7, 405 exercised cases; `B1_injection_noproj.md`, `B1_injection_proj.md`)
| Injection | exercised | false auto-accept | false READY |
|---|---|---|---|
| E1 one digit (one doc) | 42 | 0 | 0 |
| E2 same substitution on every doc | 22 | 0 | 0 |
| E3 transposition (one / all docs) | 43 / 22 | 0 / 0 | 0 / 0 |
| E4 digit dropped/duplicated | 44 | 0 | 0 |
| E5 name character (one / all docs) | 36 / 18 | 0 / 0 | 0 / 0 |
| E6 expired → valid date | 4 | 0 | 0 |
| E7 company name (one / all docs) | 46 / 24 | 0 / 0 | 0 / 0 |
| E8 GPA crossing threshold | 18 | 0 | 0 |
| E9 student number | 32 | 0 | 0 |
| **Common-mode ("-both"): E6 / E8 / E9** | 4 / 18 / 32 | **1 / 18 / 4** | 0 |

Single-document: 0 false auto-accepts and 0 false READY. Correlated: 0 / 0, with or without application values (S7). **Residual risk (stated):** if an OCR misread repeats *identically in both independent passes* and nothing else (another document, the application) can confirm the field — dates, GPA, student numbers on a lone document — S7 auto-accepts it (23 cases). The injection assumes this for every case (worst case); it needs the same wrong digit read twice from differently preprocessed crops. In those 23 cases the submission still ended REVIEW_REQUIRED/NEEDS_CORRECTION because other fields blocked it, but a submission with nothing else to block it could reach READY. A check-digit-preserving transposition is also not caught by the check digit itself (S6/S7 catch it through the second-pass veto; shown by a unit test because the development numbers contain none).

## 6. D4 items (tests first, each committed)
- **Multi-document files:** pages classified individually; different supported types → `MULTIPLE_DOCUMENTS_IN_FILE`, fields extracted from the first type's pages only, REVIEW_REQUIRED at document and submission level. F13: 4/4 flagged; F12/F14 unchanged.
- **Student issue date:** implemented per decision 1 (S01, S10 digital READY; S08 unresolved).
- **B09:** `notices` list in the verification response (`DUPLICATE_UPLOAD_IGNORED`, status effect READY, persisted and reloaded).
- **OCR word joining:** investigated: the dropped spaces (`주식회사테스트상사`) come from *inside single recognised boxes*, not from how boxes are joined; the gap-based joining (abutting boxes → no space) is implemented, and a glued college/department splitter handles `공과대학기계공학과`. Whole-box space loss cannot be repaired by geometry.
- **Transcript classification on scans:** cause was reading order (fixed 12-px bands scrambled the letter-spaced title boxes) — now row-by-overlap; plus transcript layout signals (`취득학점`, `백분율`) and `재학기간` for enrolment certificates. Transcript scanned 1/9 → 9/9, images 6/9 → 9/9.
- Extra fixes found on the development set: submitter company-name comparison now tolerates legal-entity notation (B02 with application values), stacked two-line labels centred between lines, spilled `)` in value cells, small box overlap tolerance.

## 7. B0 vs B1 — development set (`compare_runs.py`)
| Metric | B0 | B1 (S7) |
|---|---|---|
| digital CORRECT / WRONG | 240 / 0 | 240 / 0 |
| scanned CORRECT / WRONG / UNRESOLVED (of 240) | 139 / 3 / 98 | 228 / 0 / 12 |
| images CORRECT / WRONG / UNRESOLVED | 199 / 1 / 40 | 230 / 0 / 10 |
| OCR fields auto-accepted (scanned / images) | 0 / 0 | 71.7 % / 74.2 % (73.3 / 75.8 % with application values) |
| false auto-accept | 0 | 0 |
| review burden per submission (scanned / images) | 11.64 / 11.64 | 3.82 / 3.55 (**−67 % / −70 %**); 3.64 / 3.36 with application values |
| auto-decided submissions (scanned / images) | 1/22, 1/22 | 4/22, 7/22 (same with application values) |
| false READY | 0 | **2 (S02, S09 digital — disputed, below)** |
Highlights: scanned and image B01 reach READY by themselves; B02 images too; S01, S10 digital READY; S08 REVIEW_REQUIRED; B10 REVIEW_REQUIRED with the checksum code.

## 8. Hold-out judgement (run once; aggregates only; `holdout_compare.md`, `H_*_report.md`)
| Metric | B0 | B1 |
|---|---|---|
| digital fields CORRECT / WRONG / UNRESOLVED (of 275) | 174 / 0 / 101 | 174 / 0 / 101 |
| scanned | 175 / 5 / 95 | 251 / 0 / 24 |
| images | 212 / 7 / 56 | 255 / 0 / 20 |
| OCR fields auto-accepted (scanned / images) | 0 % / 0 % | 68.4 % / 70.9 % (70.9 / 73.5 % with application values) |
| false auto-accept | 0 | 0 |
| review burden (scanned / images) | 11.64 / 11.64 | 4.12 / 3.72 (**−65 % / −68 %**); 3.84 / 3.44 with application values |
| auto-decided submissions | 1/25, 1/25 | 5/25, 6/25 |
| false READY | 0 | **1 — B11/images (look-alike document)** |
| acted-on wrong fields | 0 | 0 |
H13 (one-character company-name difference): REVIEW_REQUIRED in all versions. H14 (swapped digits on three certificates): NEEDS_CORRECTION (digital), REVIEW_REQUIRED (scanned, images). H15 (student number one digit off): REVIEW_REQUIRED in all versions. None READY; no corroboration across the near-miss values.

**Development vs hold-out — overfitting, stated plainly.**
1. *Digital extraction does not generalise to the hold-out layouts:* digital fields 174/275 correct (63 %) vs 240/240 on the development set, and B0 = B1 (no change from this phase). By type (digital CORRECT of N): SME confirmation **0/56**, enrolment 20/48, business registration 14/28, tax 42/42, social insurance 41/41, transcript 57/60. Classification is 100 % on the hold-out digital documents, so the failures are extraction of layouts that differ from the seven development layouts. Phase C's fixes were developed against those seven layouts; this is the clearest overfitting signal in the project and the main next-phase item. No value was wrong (0 WRONG): the failures abstain.
2. *The auto-acceptance mechanism generalises:* auto-accept rate (68–74 %) and burden reduction (−65/−68 %) are close to the development set (72–74 %, −67/−70 %), with 0 false auto-accepts. It is limited by extraction, not by the decision rules.
3. *Safety failure on the hold-out:* **B11/images is READY (false READY).** The 지방세 look-alike was OCR'd with a garbled title, escaped the look-alike list, was classified as the national-tax certificate, and its fields were auto-accepted as corroborated. The development set did not expose it (its look-alike scans were recognised). This violates the acceptance criterion and must be fixed first (see §10). No wrong *value* was accepted; the error is a wrong document type.

## 9. Acceptance table
| Criterion | Result |
|---|---|
| False READY: development, hold-out, all injections | **FAIL** — dev 2 (S02/S09 digital: disputed expectations, §10), hold-out 1 (B11/images look-alike); injections 0 |
| False auto-accept: development, hold-out, single-document injections | **PASS** — 0 / 0 / 0 |
| Correlated injections | **PASS (reported)** — S7: 0 false auto-accept, 0 false READY, with and without application values; common-mode residual stated in §5 |
| H13 / H14 / H15 | **PASS** — never READY, no corroboration across near-misses |
| Review burden scanned/images lower than B0 | **PASS** — dev −67 / −70 %, hold-out −65 / −68 % |
| Scanned/image B01 auto-decided READY | **PASS** (development; B01 and B02-images READY) |
| S01/S10 digital READY; S08 REVIEW_REQUIRED | **PASS** on the development set |
| F13 flagged; F12, F14 unchanged or better | **PASS** |
| Digital WRONG not higher; digital CORRECT not lower | **PASS** (240/0 → 240/0; hold-out 174/0 → 174/0) |
| Hold-out vs development gap | **FAIL (explained)** — digital extraction 63 % vs 100 %; auto-accept rate and burden reduction consistent |
| Overfitting grep (development and hold-out values) in production code | **PASS** — 0 hits (51 values checked over the whole production tree) |
| Quality gates | **PASS** — 495 backend tests, ruff, format, mypy |

## 10. Remaining problems / needs your decision
1. **B11/images false READY (hold-out).** Fix next: a look-alike must not become READY when the OCR text lacks its title but carries look-alike structure (e.g. 지방세/시·군·구 issuers, a local-tax form's section labels), and a document classified by weak/ambiguous OCR evidence should not have its fields auto-accepted for a required national document without a strong title signal.
2. **Digital extraction on unseen layouts** (SME 0/56, enrolment, business registration): extraction was fitted to seven layouts; needs layouts from more real forms.
3. **S02 and S09 digital are READY (dev), both disputed expectations, not wrong values:** the seeded student workflow has no ISSUE_DATE_MAX_AGE rule (with a 90-day rule configured S02 is NEEDS_CORRECTION and S01 stays READY — verified), and `student_id` is not a required field of the default enrolment requirement (certificates that print no student number would otherwise never be READY). Marked EXPECTATION_DISPUTED for you to decide.
4. READY on rows the manifest leaves "record actual": S04, S05, S06 digital (S05 = transcript with a different name: the default student workflow has no enrolment-vs-transcript comparison rule, so it is READY unless an applicant name is entered), B06, B09. Configure comparison rules if these should block.
5. Common-mode OCR errors on lone dates/GPA/student numbers (§5).
6. Application values improve S7 modestly on the development set; the default product mode (none entered) is the headline.

## 11. How a reviewer sees an auto-accepted field
`GET /documents/{id}` → each field has `auto_acceptance`: `accepted`, `rule_id` (e.g. `BRN:DOCUMENTS`, `DATE:SECOND_PASS`, `COMPANY:APPLICATION+DOCUMENTS`), `sources` (`documents` / `application` / `second_pass`), `corroborating_document_ids`, `second_pass_value`, `strategy`, `policy_version`, and — when *not* accepted — `reason` (e.g. `DISAGREES_WITH_OTHER_DOCUMENT`, `CONFLICTS_WITH_APPLICATION_VALUE`, `NO_INDEPENDENT_CONFIRMATION`, `FORMAT_BRN_CHECKSUM`). `normalized_value` (machine evidence) is unchanged; `effective_normalized_value` shows the accepted value with `effective_source` MACHINE; a human review still overrides. The review queue (`/projects/{id}/reviews`) lists only fields still needing a human and carries the same object. Verification responses add `notices` (e.g. `DUPLICATE_UPLOAD_IGNORED`).

## 12. Limits
The documents are fictional and generated from the layouts of a few real samples; the hold-out showed the extraction fit to those layouts. Real documents will have more varied layouts, fonts and scan quality; the correlated and common-mode residual risks were exercised by injection, not measured on real errors. A real-document check is still recommended before the demo. The check-digit algorithm is the commonly published one and needs confirming against an official source.

## 13. Reproduce
```bash
cd apps/api
# development set (OCR recorded once, then replayed)
.venv312/bin/python ../../evaluation/harness/run_variants.py --corpus dev --output /tmp/raw.json \
  --ocr-cache ../../evaluation/phase_d/ocr_cache --ocr-mode record|replay [--project-values] [--strategy S0..S7]
python3 ../../evaluation/harness/score_v2.py --raw /tmp/raw.json --corpus dev --out-json out.json --out-md out.md
.venv312/bin/python ../../evaluation/harness/inject_errors.py --ocr-cache ../../evaluation/phase_d/ocr_cache --out /tmp/inj [--project-values] [--strategy S7]
python3 ../../evaluation/harness/compare_strategies.py ; python3 ../../evaluation/harness/compare_runs.py B0.json B1.json
# B0 = a worktree of main (production code before D3) with the harness files copied in
# FINAL-JUDGEMENT ONLY (hold-out; logs to holdout_runs.log):
ADVS_FINAL_JUDGEMENT=1 .venv312/bin/python ../../evaluation/harness/run_variants.py --corpus holdout ...
ADVS_FINAL_JUDGEMENT=1 python3 ../../evaluation/harness/score_v2.py --corpus holdout ...
```
