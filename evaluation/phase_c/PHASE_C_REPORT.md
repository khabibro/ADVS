# Phase C report — new baseline on the test set, then targeted fixes

Branch `phase-c/test-set-fixes` (from `main` @ `4f22092`). Not pushed, not merged.

## 1. Preconditions
All passed: only `main`/`origin/main`, clean tree, up to date; Phase B fixes present in code (`strip_legal_entity_markers` in `normalization/field_normalizer.py`, `UNSUPPORTED_LOOK_ALIKE_TITLES` in `classification/classifier.py`, `reference_date` threaded through validation with no `date.today()` in rule evaluation, additive required-field rules in `validation/engine.py`); manifest lists 299 files, all present, all SHA-256 match; harness runs; backend suite (408), ruff, format and mypy green.

## 2. Scorer
`evaluation/harness/score_variants.py`, SHA-256 `b0ae22b51227401144787757910d1adc7b14266933d30838d06ada4706fd8c59` (identical at B0 and B1; manifest hash also identical). Rules are in its docstring and in every report: classification = exact type; field values compared after ISO dates / 10-digit business numbers / GPA to 2 decimals / scale `4.5`/`4.3` / whitespace-collapse only for text; outcomes CORRECT / WRONG / UNRESOLVED / NOT_EVALUATED (VERIFIED_ABSENT → correct abstention or WRONG); status RECORD when the expectation says "record actual" or "or"; false READY = READY where not expected (always for scanned/images); review burden = fields with `needs_review`.
Two things I decided while writing it (both before the freeze): values are scored on the extractor's **machine** value, with the policy-gated effective value kept as a "trusted" flag (a first B0 pass scored only gated values and made all OCR fields look UNRESOLVED, so it was discarded); and one expectation is annotated `EXPECTATION_DISPUTED` without changing the outcome (§7).
The harness moved from `evaluation/phase_b/` to `evaluation/harness/` and now records raw results only; the S03/S04 "GPA rule" is the seeded student checklist, which already carries GPA ≥ 3.0.

## 3. B0 (main)
Digital: classification correct except 4대보험 (0/12); field CORRECT 106/240 (89 trusted), WRONG 2, UNRESOLVED 132; B01/B02/S01/S10 not READY; false READY 0. Details: `B0_report.md`, `B0.json`.

## 4. C1 diagnosis (`C1_diagnosis.md`)
Top causes: value cell starting with `: ` rejected by the field validators; 완납증명원 title missing; `(사업자등록번호)` parenthesised and stacked labels; no `소속` label / college prefix; university only in the issuer line; transcript cumulative GPA (row after 총 취득학점; header-table cell); unlabelled issue dates untrusted by policy. OCR-specific items are recorded in §4 of that file.

## 5. Fixes

| Fix | Cause | Files (production) | Tests (hold-out values) | Commit |
|---|---|---|---|---|
| C-1 | 완납증명원 title form (근로복지공단) missing; ambiguity margin correctly sent it to UNKNOWN | `classification/classifier.py` (+5 lines: `완납증명원` TITLE, `고용보험료`/`산재보험료` SUPPORT) | `tests/test_phase_c_classification.py`: title variants classify, 지방세 look-alike stays UNKNOWN, bare phrase doesn't classify | `bcc4445` |
| C-2 | see C1 | `extraction/base.py` (`_strip_value_cell_colon`, parenthesised-label regex and `)` skip in `_row_candidates`, `cumulative_gpa_candidates`, `issuer_university_candidate`, `stacked_label_value`, `_gpa_candidate`), `extraction/enrollment.py` (소속 label, affiliation before 전공, college-prefix removal, issuer-line university), `extraction/transcript.py` (shared issuer-line fallback replaces the local regex) | `tests/test_phase_c_extraction.py` (11 tests incl. negatives: checkbox label, two different issuer universities, conflicting semester GPAs still abstain) | `9cc05a2`, `03e1b00` |
| C-3 | F-004 | `normalization/field_normalizer.py` (`is_valid_business_number`), `extraction/base.py` (value and evidence kept, `needs_review`, method `regex_business_number_checksum_failed`), `validation/engine.py` + `validation/submission.py` + `services/verification.py` (`BUSINESS_NUMBER_CHECKSUM_FAILED`, REVIEW_REQUIRED, cleared by a human confirmation) | `tests/test_phase_c_safety.py` (valid/one-digit-changed/hyphen parity/gating/submission/configured rules/human-confirmed). Existing fixtures that used checksum-invalid sample numbers (`test_ocr_provider.py`, `test_round2_real_document_fixes.py`) now use valid ones. | `f13ce8e`, `e77cf4b` |
| C-4 | F-005 | `ocr/providers.py` (+4: `render_dpi` = per-page `effective_render_dpi`) | `tests/test_phase_c_ocr_guard.py` (downscaled page reports real DPI; normal page reports configured) | `afe3cd4` |
| C-5 | F-006 | `core/config.py` (validator: production/prod + `mock` → error) | same file (refused: 4 spellings; allowed: 5 combinations) | `822e98d` |

The check-digit algorithm is the commonly published one (weights 1,3,7,1,3,7,1,3,5; check digit `(10 − (Σ + ⌊d₉·5/10⌋) mod 10) mod 10`); **it must be confirmed against an official source**.
Quality gates at HEAD: 450 tests, ruff, format check, mypy all pass. Overfitting grep over `git diff 4f22092..HEAD -- apps/api/app` for `TEST`, `테스트상사`, `가나다솔루션`, `김테스트`, `한국가상대학교`, `가상세무서장`, `가상구청장`, `직인 생략`, manifest numbers (`220-81…`, `105-87…`, `110111…`), `박가상`, `2023123456`, `데이터공학과`, `이샘플`: **0 hits** (one docstring example from the corpus was found and replaced).

## 6. B0 vs B1 (`B0_vs_B1.md`)
13 of 14 criteria PASS. **FAIL: scanned+images field WRONG 36 → 41** (all review-gated, 0 unflagged; whitespace-dropping OCR artifacts on fields that were previously unresolved; net OCR CORRECT +60 scanned / +87 images). Highlights: digital field CORRECT 106 → 239 of 240; B01 and B02 READY; B10 REVIEW_REQUIRED + `BUSINESS_NUMBER_CHECKSUM_FAILED`; B07 partial-checklist REVIEW_REQUIRED; digital status MATCH 7 → 12 (of 23 scored/recorded rows; 5 MISMATCH remain); F16 all rejected at upload; scanned/images never READY; review burden digital 8.5 → 3.3 fields per submission.

## 6a. Decisions recorded after review
- **Accepted exception:** the one failed criterion (scanned/image field WRONG 36 → 41) is accepted. All 5 additional values are review-gated whitespace artefacts of OCR (0 unflagged).
- **Resolved in the system's favour:** the B02-3 `㈜`/`(주)` dispute is NFKC-equivalent text; the scorer will adopt that rule in the next phase, not retroactively (B0/B1 numbers stay as measured).
- The fictional test set is the main evaluation corpus; the real-document check is not required for this merge (limit in §9 stands as a caveat on the numbers).

## 7. Disputed expectations (manifest untouched)
- `B02-3_납세증명서.pdf / company_name`: manifest `㈜` (U+3231) vs system `(주)` after Unicode NFKC. `EXPECTATION_DISPUTED` — same text; remains the one digital WRONG. **Resolved (see 6a): NFKC-equivalent, system correct.**
- Not disputed but worth your decision: B11/S07 digital expect NEEDS_CORRECTION; the system returns REVIEW_REQUIRED whenever an UNKNOWN document is present (design). S01/S10 expect READY; see below.

## 8. Remaining problems for the next phase
1. **Student certificates cannot be READY** (S01, S10; S02 can't be NEEDS_CORRECTION): every printed issue date is an unlabelled bare date in the issuance block → `SEMANTIC_INFERENCE` → untrusted. Needs a policy decision (trust a bare date next to an issuer line on embedded text?) or a manifest change. Not touched (evidence policy is out of scope).
2. **B09 duplicate**: identical uploads are collapsed at submission level; the submission is READY and only the copy carries `DUPLICATE_UPLOAD`. Manifest says "duplicate flagged".
3. **Multi-page documents newly exposed**: F12/F13/F14 digital PDFs (certificate + unrelated page / second certificate / blank page) now reach document-level READY (B0 hid this because nothing was extracted). F13 ("two different certificates in one PDF") should be flagged. Check that no field is taken from page 2 and that mixed-type PDFs raise a review.
4. **OCR**: transcript classification 1/9 scanned and 6/9 images (letter-spaced title/labels not recognised); enrollment 7/9 scanned; dropped-space values (`주식회사테스트상사`, `공과대학데이터공학과`); social-insurance classification on OCR is now fixed (12/12) but OCR field recall is still partial (UNRESOLVED 98 scanned, 40 images). F07/F08/F11 rotated/photo cases keep ≥ 1 misclassification each.
5. TIFF/BMP/DOCX are rejected at upload (F15, 6/6) — confirm that is intended.
6. Layout understanding beyond this phase: the cumulative-GPA, stacked-label and issuer-line rules are geometry heuristics tuned to the layouts of a few real samples.
7. Verify the business-number check-digit algorithm against an official source before relying on it.

## 9. Limits of this result
The test set is fictional and built on the layouts of a few real samples, and the fixes were developed against its layouts (each with hold-out unit tests, but the same families of forms). Digital accuracy of 239/240 is therefore **not** a real-world accuracy estimate. A final check on real documents (from `~/ADVS_archive_20261004/`) is still required before the mentor demo.

## 10. Reproduce
```bash
git checkout phase-c/test-set-fixes          # B1; use `git checkout 4f22092` for B0 (harness/scorer then come from f45402e)
cd apps/api
.venv312/bin/python ../../evaluation/harness/run_variants.py --output /tmp/raw.json
python3 ../../evaluation/harness/score_variants.py --raw /tmp/raw.json \
  --out-json ../../evaluation/phase_c/B1.json --out-md ../../evaluation/phase_c/B1_report.md --label B1
shasum -a 256 ../../evaluation/harness/score_variants.py   # must equal b0ae22b5…080c
# gates
.venv312/bin/ruff check . && .venv312/bin/ruff format --check . && .venv312/bin/mypy --explicit-package-bases app && .venv312/bin/pytest -q
```
For B0 on the original code: `git stash`-free route is `git worktree add /tmp/b0 4f22092`, copy `evaluation/harness/*` from `f45402e` into it, and run the same two commands there.
