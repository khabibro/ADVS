# B0 vs B1 — acceptance table

Same harness, same scorer (SHA-256 `b0ae22b51227401144787757910d1adc7b14266933d30838d06ada4706fd8c59`, **unchanged**), same manifest (hash unchanged), same clock (2026-10-05). B0 = main `4f22092`; B1 = branch `phase-c/test-set-fixes` HEAD (see `B1_report.md`).

| Criterion | Required | B0 | B1 | Result |
|---|---|---|---|---|
| False READY (all sets, all versions) | 0 | 0 | 0 | **PASS** (see note 1) |
| Field WRONG — digital | ≤ B0 | 2 | 1 (the disputed `㈜`/`(주)` NFKC case; the other B0 WRONG, S09 department, is fixed) | **PASS** |
| Field WRONG — scanned + images | ≤ B0 | 36 (12 + 24) | 41 (15 + 26) | **FAIL** (note 2) |
| Field CORRECT — digital | > B0 | 106 / 240 (89 trusted) | 239 / 240 (218 trusted) | **PASS** (+133) |
| Classification — digital | every type correct | social-insurance 0/12 | all types 100 % (9 types incl. UNKNOWN look-alikes 3/3) | **PASS** |
| B01 digital | READY or cause named | REVIEW_REQUIRED | READY | **PASS** |
| S01, S10 digital | READY or cause named | REVIEW_REQUIRED | REVIEW_REQUIRED — only cause: `issue_date` unlabelled bare date → `SEMANTIC_INFERENCE` → effective value unavailable (evidence-sufficiency policy, out of scope) | **PASS (cause named)** — not READY |
| B02 digital | READY | REVIEW_REQUIRED | READY | **PASS** |
| B07 digital, partial checklist | REVIEW_REQUIRED | REVIEW_REQUIRED (for the wrong reason: nothing was read) | REVIEW_REQUIRED (`REQUIRED_FIELD_UNRESOLVED`, valid_until absent) | **PASS** |
| B10 digital | REVIEW_REQUIRED + checksum code | REVIEW_REQUIRED (nothing read) | REVIEW_REQUIRED, `BUSINESS_NUMBER_CHECKSUM_FAILED` | **PASS** |
| B11, S07 | look-alikes UNKNOWN, never READY | UNKNOWN 3/3, REVIEW_REQUIRED | UNKNOWN 3/3 (all versions), REVIEW_REQUIRED (manifest expects NEEDS_CORRECTION → scored MISMATCH, see note 3) | **PASS** |
| Scanned and image versions | never READY | 0 READY | 0 READY | **PASS** |
| F16 corrupt files | FAILED/rejected, no crash, never READY | 6/6 rejected (400) | 6/6 rejected (400), no 5xx | **PASS** |
| Overfitting grep | no test-set values in production code | — | 0 hits across `git diff 4f22092..HEAD -- apps/api/app` | **PASS** |
| Quality gates | suite, ruff, format, mypy pass | pass | 450 tests pass; ruff, format, mypy clean | **PASS** |

**One criterion fails: scanned/image WRONG 36 → 41.**

## Notes

1. **False READY = 0 by the scorer's definition**, but two digital RECORD rows ended READY and need a human look: **B06** (validity ends on the submission date; manifest says READY if inclusive — expected) and **B09** (same 납세증명서 uploaded twice plus a renamed copy). In B09 the copy gets a document-level `DUPLICATE_UPLOAD` (REVIEW_REQUIRED) but the submission collapses identical checksums and is READY. I did not change this (out of scope, and arguably intended); the manifest's own text says "duplicate flagged", so it is listed as a problem for the next phase.
2. **Scanned/image WRONG +5** (scanned +3: 12→15; images +2: 24→26). All five are fields that were *unresolved* at B0 and are now *read*, and are 100 % review-gated (0 unflagged WRONG, as at B0): three are the existing OCR whitespace artifact `주식회사테스트상사` (OCR drops the space after 주식회사; the frozen scorer compares whitespace-collapsed only), two are `department` `공과대학데이터공학과` (OCR dropped the space between college and department, so the college-prefix removal, which splits on spaces, does not apply). Net effect on OCR: CORRECT scanned 67 → 127, images 87 → 174, UNRESOLVED 161 → 98 / 129 → 40. No OCR value reaches a decision without human confirmation. A glued-prefix rule for department could remove two of the five, but it would not make this criterion pass (three space-artifact WRONGs remain), so I left it.
3. B08/B11/S07 mismatches: B08 now correct (NEEDS_CORRECTION `MISSING_REQUIRED_DOCUMENT`). B11/S07 expect NEEDS_CORRECTION but the design returns REVIEW_REQUIRED when any UNKNOWN document is present (`UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW`); unchanged.

## Status matches (scored rows)

| Version | B0 MATCH / MISMATCH / RECORD | B1 MATCH / MISMATCH / RECORD |
|---|---|---|
| digital | 7 / 10 / 6 | 12 / 5 / 6 |
| scanned | 15 / 3 / 4 | 16 / 2 / 4 |
| images | 15 / 3 / 4 | 16 / 2 / 4 |

Remaining digital MISMATCH (5): S01, S10 (issue_date policy), S02 (issue-date-age rule can't fire on an untrusted date → REVIEW_REQUIRED instead of NEEDS_CORRECTION), B11, S07 (design).

## Field CORRECT by document type (B0 → B1, WRONG B0 → B1)

| Type | digital | scanned | images |
|---|---|---|---|
| 사업자등록증 (of 24) | 12→24, W 0→0 | 12→12, W 7→7 | 12→12, W 12→12 |
| 재학증명서 (of 43) | 8→43, W 1→0 | 6→28, W 1→3 | 8→40, W 1→1 |
| 납세증명서 (of 36) | 23→35, W 1→1* | 20→22, W 4→4 | 13→19, W 11→11 |
| 중소기업확인서 (of 48) | 36→48, W 0→0 | 26→37, W 0→1 | 36→48, W 0→0 |
| 4대보험 (of 35) | 0→35, W 0→0 | 0→23, W 0→0 | 0→24, W 0→2 |
| 성적증명서 (of 54) | 27→54, W 0→0 | 3→5, W 0→0 | 18→31, W 0→0 |

\* the disputed `㈜` case.

Review burden (fields needing a human, mean per submission): digital 8.5 → 3.3, scanned 7.5 → 5.9, images 7.8 → 4.9. Processing time unchanged (digital ≈ 30 ms/doc, scanned ≈ 11.5 s, images ≈ 9 s).
