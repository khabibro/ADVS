# C1 — Diagnosis of B0 failures (no fixes applied)

Source: `evaluation/phase_c/B0.json` (main @ `4f22092`), plus a per-document trace of every digital file through the text-layer path (`PdfProcessor.extract_text` → classifier → extractor), with rows and bounding boxes inspected. All line numbers refer to `apps/api/app/document_intelligence/` on main.

## 1. Failures ranked by impact (digital versions)

| # | Failure | Stage | Root cause | Affected (digital) |
|---|---|---|---|---|
| 1 | `company_name`, `representative_name`, `student_name`, `student_id`, `department` unresolved on letter-spaced "label cell + value cell" layouts | value association | The value cell is a separate text box that **starts with `: `** (`: 주식회사 …`). `_row_candidates` takes the whole cell as the value (`extraction/base.py:406`, `:425`), and the field-shape validators then reject it because it contains `:` (`extraction/fields.py` `is_organisation`, `is_person_name`, `is_free_text` all reject `":" in stripped`). Label matching itself works (spaces inside labels are tolerated). | 사업자등록증 company_name 12/12; 중소기업확인서 company_name 12/12; 재학증명서 student_name 9/9, student_id 8/8 (+2 verified-absent correct), department; transcript is spared only because it has a `성명 :` in one box |
| 2 | Social-insurance certificate classified UNKNOWN | classification | Real form title is **"완납 증명원"** (근로복지공단 form: 고용·산재보험료 완납증명원). Signals only contain the `…증명서` forms (`classification/classifier.py:116-122`). Score 4.0 (사업장명 + 사업자등록번호) ties with 사업자등록증 and 중소기업확인서 on shared labels, the ambiguity margin (`:AMBIGUITY_MARGIN`) correctly sends it to UNKNOWN. | 12/12 social-insurance docs → all 35 evaluated fields unresolved; **blocks READY in B01–B12** (a required document is UNKNOWN) |
| 3 | 납세증명서 `business_registration_number` unresolved | label match | The number sits in a cell labelled `주민등록번호 / (사업자등록번호)`: the label is **parenthesised**. `_row_candidates` requires the label at row start or after whitespace (`base.py:379`: `(?:^|[ \t])label`), so `(사업자등록번호)` never matches. | 12/12 tax certificates |
| 4 | Social-insurance `business_registration_number` | label/value geometry | Two-line stacked label cell `사업자등록번호` / `(법인등록번호)`; the value is vertically centred beside the *second* line. Only the second line overlaps the value by ≥ 50 % of height, so `_right_associated` (`base.py:330`) fails for the line that carries the label. A check-box row `☐ 사업자등록번호` (발급기준) is a distractor. | 12/12 (after fix 2) |
| 5 | Transcript `gpa` / `gpa_scale` unresolved | candidate selection | Layout A prints one `평점평균: x/4.5 백분율: y/100` per semester; the cumulative one follows `총 취득학점`. Values contain trailing `백분율…`, so `normalize_gpa` (`normalizer:GPA_RE.fullmatch`) fails for every candidate → unresolved (the safe outcome, but no value). Layout B (S10 table-style) prints the cumulative GPA in a header-table cell under `총평점평균` (`3.80 / 4.5`) — no label/value on a shared row, so the row-based matcher never sees it. | 9/9 transcripts (gpa + gpa_scale) |
| 6 | `university_name` unresolved | label match | Enrollment/transcript certificates print no `대학교` label; the university appears only in the issuer line (`한국…대학교 총장`, sometimes letter-spaced `한 국 … 대 학 교 총 장`). The transcript fallback regex (`extraction/transcript.py:_STANDALONE_UNIVERSITY_RE`) needs a full-line `…대학교` match and the enrollment extractor has no fallback at all. | 9/9 enrollment, 9/9 transcript |
| 7 | `department` unresolved; once readable, picks the wrong label | label alias | Real form label is **소속** (`공과대학 데이터공학과`); the extractor only knows `학과`/`전공` (`extraction/enrollment.py`). On the bordered layout (S09) a separate `전공` row exists, so after fix 1 the `전공` value (a different thing) would win → `WRONG`. Today S09 already yields `WRONG` (`데이터사이언스전공` vs manifest `데이터공학과`) because the `전공` cell is read via the spatial path. | 9/9 enrollment; 1 WRONG (S09-1) |
| 8 | Social-insurance `valid_until` unresolved (11/11) | classification | Same as 2 (never extracted). Layout prints `2026년 10월 31일 까지` which the date regex accepts. | 11 (+1 correctly absent) |
| 9 | `issue_date` machine-correct but **not trusted** | evidence policy | Unlabelled bare issue dates are read by `standalone_date_candidate` and deliberately marked `needs_review` (`base.py` `issue_date_field`, method `document_semantic_issue_date`) → `SEMANTIC_INFERENCE` → `REVIEW_REQUIRED` in `evidence_sufficiency.py`. 17 digital fields (enrollment 8, transcript 9) are CORRECT but gated. Submission verification then reports `OCR_UNCERTAIN` for them. | 17 fields; **blocks READY on every set whose documents print the date unlabelled** |
| 10 | 납세증명서 B02-3 `company_name` WRONG | normalization | The manifest value uses `㈜` (U+3231); extraction applies NFKC (`normalize_lexical_text`) and returns `(주)`. Same text, different code points. Not a system error → `EXPECTATION_DISPUTED` (see report). | 1 |
| 11 | Digital `B08` / `B11` / `S07` status mismatch | status | Follow-on of 2 / 9: required documents UNKNOWN produce `UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW` (REVIEW_REQUIRED) instead of `MISSING_REQUIRED_DOCUMENT` (NEEDS_CORRECTION). By design: with an UNKNOWN document present the system cannot say a type is missing. S07/B11 expect NEEDS_CORRECTION with `UNKNOWN` look-alikes — this conflicts with that design (see §3). | B08, B11, S07 (3 submissions × 3 versions) |

## 2. What blocks READY on the digital sets

| Set | Blocking causes today | After C-1/C-2 (expected) |
|---|---|---|
| B01, B02 | social-insurance UNKNOWN (#2); company_name missing (#1); 납세증명서 BRN (#3); issue_date untrusted (#9 — business certificates print the issue date unlabelled) | #2/#1/#3 fixable; **#9 is a policy matter** |
| S01, S10 | enrollment fields (#1, #6, #7); transcript gpa/university (#5, #6); issue_date untrusted (#9) | #1/#5/#6/#7 fixable; **#9 remains** |
| B07 | the partial-checklist (F-001) case already behaves (REVIEW_REQUIRED) — but only because everything else is unresolved too | to be proven end-to-end after fixes |
| B10 | same: REVIEW_REQUIRED for the wrong reason (nothing is read). The check-digit rule does not exist yet (F-004) | C-3 |

**Finding #9 is decisive for the READY expectations.** `issue_date` is a default required field of every modelled type, and every certificate in the corpus prints it as a bare date in the issuance block. Under the current evidence policy such a date is a *semantic inference* and always needs human confirmation, so no all-valid digital submission can be READY regardless of extraction quality. The Phase C rules forbid touching the evidence policy, so READY for B01/S01/S10 cannot be reached in this phase; the remaining cause will be named exactly in the B1 report. The user should decide (a) policy change (a bare date inside an issuance block with a nearby issuer line is trustworthy for digital text) or (b) change the manifest expectation for digital sets to REVIEW_REQUIRED.

## 3. Expectation disputes (recorded, manifest not edited)

- `B02-3_납세증명서.pdf / company_name`: `㈜` vs `(주)` (NFKC). `EXPECTATION_DISPUTED` — annotated in the scorer report.
- B08/B11/S07 digital expect `NEEDS_CORRECTION` / `MISSING_REQUIRED_DOCUMENT`; current design returns `REVIEW_REQUIRED` + `UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW` whenever any UNKNOWN document is present (`validation/submission.py:482`). Not scored as dispute; reported as MISMATCH at B1 unless the user decides otherwise.
- `S09-1 department`: manifest expects the 소속 value (`데이터공학과`, college prefix dropped) rather than the 전공 row. Followed as written.

## 4. OCR-specific failures (recorded, not fixed in this phase)

| Failure | Count | Note |
|---|---|---|
| Social-insurance classified UNKNOWN on scans/images | 24 | same signal gap as #2 → fixed by C-1 if the OCR text carries `완납 증명원`; re-measured at B1 |
| Transcript classified UNKNOWN on scans/images | scanned 8/9, images 3/9 | OCR does not recover the letter-spaced title `성 적 증 명 서` / `평점평균` reliably (OCR recognition) |
| Enrollment UNKNOWN (scanned) | 2/9 | same |
| `company_name` WRONG on images/scans (space dropped: `주식회사테스트상사`) | scanned 7, images 12 | Recognition drops the space after 주식회사. Scorer rule is whitespace-collapse **only**, so these count as WRONG; all are review-gated (0 unflagged). Not a system extraction error. |
| Fields UNRESOLVED/WRONG on OCR in general | scanned 12 WRONG / images 24 WRONG, 0 unflagged | all OCR values are gated to review by policy |

Every OCR field is gated to human review by policy, so scanned and image submissions never reach READY (verified: 0 false READY at B0).

## 5. Summary for the fix list

- **C-1**: add the real title form `완납증명원` (+ supporting `고용보험료`/`산재보험료` labels) → #2, #8.
- **C-2** (by cause): value-cell leading colon (#1); parenthesised labels (#3); two-line stacked labels (#4); `소속` label + college-prefix handling with affiliation-before-major priority (#7); issuer-line university (#6); cumulative GPA (row after `총 취득학점`; header-table cell) (#5).
- **Not fixed (documented)**: #9 evidence policy (forbidden scope), #10 scorer vs NFKC, #11 design, and all OCR-recognition items.

## 6. Addendum after B1 (correction)

§2/#9 predicted that the untrusted bare issue date would block READY on all digital sets. B1 showed this is only true for the **student** certificates: `issue_date` is a default required field of 재학증명서/성적증명서, but not of the four business documents, so B01/B02 reach READY once the other causes are fixed. S01/S10 remain REVIEW_REQUIRED solely because of `issue_date` (`SEMANTIC_INFERENCE`, effective value UNAVAILABLE).
