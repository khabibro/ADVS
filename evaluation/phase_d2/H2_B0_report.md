# HOLD-OUT-2 B0 report (scorer v2)

- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; manifest SHA-256 `13f5c9d4da32d8683e74afda6c50b6c0607fbf0cf6162a98d83b48780ca398b0`
- Corpus `holdout2`, git `110ead2`, strategy `None`, project values `False`

## 1. Submission status per set × version

| Set | Version | Expected | Actual | Result | Notes |
|---|---|---|---|---|---|
| B01 | digital | READY | REVIEW_REQUIRED | MISMATCH |  REQUIRED_FIELD_UNRESOLVED |
| B01 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B01 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B02 | digital | READY | REVIEW_REQUIRED | MISMATCH |  REQUIRED_FIELD_UNRESOLVED |
| B02 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B02 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B03 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH |  REQUIRED_FIELD_UNRESOLVED |
| B03 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B03 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B04 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH |  REQUIRED_FIELD_UNRESOLVED |
| B04 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B04 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B05 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  EXPIRED_DOCUMENT, REQUIRED_FIELD_UNRESOLVED |
| B05 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B05 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B06 | digital | READY (if expiry is inclusive) — record actual | REVIEW_REQUIRED | RECORD |  REQUIRED_FIELD_UNRESOLVED |
| B06 | scanned | (digital expectation) READY (if expiry is inclusive) — record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B06 | images | (digital expectation) READY (if expiry is inclusive) — record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B07 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | digital_partial_checklist | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B08 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT, REQUIRED_FIELD_UNRESOLVED |
| B08 | scanned | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B08 | images | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B09 | digital | record actual | REVIEW_REQUIRED | RECORD | duplicate notice visible=False REQUIRED_FIELD_UNRESOLVED |
| B09 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B09 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B10 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED, REQUIRED_FIELD_UNRESOLVED |
| B10 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B10 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B11 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED, UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED, UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B12 | digital | NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW, REQUIRED_FIELD_UNRESOLVED |
| B12 | scanned | (digital expectation) NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B12 | images | (digital expectation) NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| H13 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH |  REQUIRED_FIELD_UNRESOLVED |
| H13 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| H13 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| H14 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  INFORMATION_MISMATCH, REQUIRED_FIELD_UNRESOLVED |
| H14 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| H14 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S01 | digital | READY | REVIEW_REQUIRED | MISMATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S01 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S01 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S02 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S02 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S02 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S03 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED, RULE_CONDITION_NOT_MET |
| S03 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S03 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S04 | digital | record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S04 | scanned | (digital expectation) record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S04 | images | (digital expectation) record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S05 | digital | record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S05 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S05 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S06 | digital | record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S06 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S06 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S07 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S08 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S08 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S08 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | trusted-wrong S09-1_재학증명서.pdf:department OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S10 | digital | READY | REVIEW_REQUIRED | MISMATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S10 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S10 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| H15 | digital | record actual — must not auto-accept student_id as corroborated | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| H15 | scanned | (digital expectation) record actual — must not auto-accept student_id as corroborated | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| H15 | images | (digital expectation) record actual — must not auto-accept student_id as corroborated | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |

Status totals: {"digital": {"MISMATCH": 8, "MATCH": 11, "RECORD": 7}, "scanned": {"CONSERVATIVE": 11, "RECORD": 7, "MATCH": 7}, "images": {"CONSERVATIVE": 11, "RECORD": 7, "MATCH": 7}}

## 2. Classification

| Type | Version | Match / total | Mismatch |
|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | digital | 14/14 | 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | images | 14/14 | 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | scanned | 14/14 | 0 |
| ENROLLMENT_CERTIFICATE | digital | 10/10 | 0 |
| ENROLLMENT_CERTIFICATE | images | 10/10 | 0 |
| ENROLLMENT_CERTIFICATE | scanned | 9/10 | 1 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | digital | 14/14 | 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | images | 14/14 | 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | scanned | 14/14 | 0 |
| SME_CONFIRMATION_CERTIFICATE | digital | 14/14 | 0 |
| SME_CONFIRMATION_CERTIFICATE | images | 14/14 | 0 |
| SME_CONFIRMATION_CERTIFICATE | scanned | 14/14 | 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | digital | 14/14 | 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | images | 14/14 | 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | scanned | 14/14 | 0 |
| TRANSCRIPT | digital | 10/10 | 0 |
| TRANSCRIPT | images | 9/10 | 1 |
| TRANSCRIPT | scanned | 9/10 | 1 |
| UNKNOWN | digital | 3/3 | 0 |
| UNKNOWN | images | 2/3 | 1 |
| UNKNOWN | scanned | 3/3 | 0 |

## 3. Field outcomes (machine value) and OCR auto-acceptance

| Version | CORRECT | WRONG | UNRESOLVED | of N | acts (effective value) | acts correct | AUTO_ACCEPTED | false auto-accept | auto-accept rate |
|---|---|---|---|---|---|---|---|---|---|
| digital | 176 | 1 | 98 | 275 | 158 | 157 | 0 | 0 | n/a |
| scanned | 219 | 0 | 56 | 275 | 0 | 0 | 0 | 0 | 0.0% |
| images | 235 | 2 | 38 | 275 | 0 | 0 | 0 | 0 | 0.0% |

Absent-field checks (VERIFIED_ABSENT): {"digital": {"NE_CORRECT_ABSTENTION": 3}, "scanned": {"NE_CORRECT_ABSTENTION": 3}, "images": {"NE_CORRECT_ABSTENTION": 3}}

| Type | Version | CORRECT | WRONG | UNRESOLVED | of N |
|---|---|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | digital | 16 | 0 | 12 | 28 |
| BUSINESS_REGISTRATION_CERTIFICATE | images | 28 | 0 | 0 | 28 |
| BUSINESS_REGISTRATION_CERTIFICATE | scanned | 27 | 0 | 1 | 28 |
| ENROLLMENT_CERTIFICATE | digital | 20 | 1 | 27 | 48 |
| ENROLLMENT_CERTIFICATE | images | 43 | 2 | 3 | 48 |
| ENROLLMENT_CERTIFICATE | scanned | 42 | 0 | 6 | 48 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | digital | 42 | 0 | 0 | 42 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | images | 33 | 0 | 9 | 42 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | scanned | 31 | 0 | 11 | 42 |
| SME_CONFIRMATION_CERTIFICATE | digital | 0 | 0 | 56 | 56 |
| SME_CONFIRMATION_CERTIFICATE | images | 55 | 0 | 1 | 56 |
| SME_CONFIRMATION_CERTIFICATE | scanned | 49 | 0 | 7 | 56 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | digital | 41 | 0 | 0 | 41 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | images | 32 | 0 | 9 | 41 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | scanned | 27 | 0 | 14 | 41 |
| TRANSCRIPT | digital | 57 | 0 | 3 | 60 |
| TRANSCRIPT | images | 44 | 0 | 16 | 60 |
| TRANSCRIPT | scanned | 43 | 0 | 17 | 60 |

## 4. Safety

- False READY: **0** []
- Effective (acted-on) values that are WRONG: ['S09/digital:S09-1_재학증명서.pdf:department']
- READY on RECORD rows (digital): []
- Duplicate-notice expectation: ['B09: visible=False']

## 5. Review burden and automatic decisions

| Version | needs-human fields / submission (mean) | total | all-flagged / submission (v1 style) | auto-decided submissions | of which equal to digital expectation |
|---|---|---|---|---|---|
| digital | 5.32 | 133 | 8.72 | 0/0 | 0 |
| scanned | 11.64 | 291 | 5.96 | 1/25 | 1 |
| images | 11.64 | 291 | 5.24 | 1/25 | 1 |

## 6. Processing time per document (ms)

| Version | Mean | Max |
|---|---|---|
| digital | 39.6 | 77.7 |
| scanned | 17083.5 | 37782.3 |
| images | 12748.0 | 32633.9 |

## 7. Format sets

| Set | Title | Files | Classification MATCH/scored | Processed | Document statuses |
|---|---|---|---|---|---|
| F02 | Scanned PDF (image only, 200 DPI) | 8 | 8/8 | 8 | {'REVIEW_REQUIRED': 8} multi-doc-flagged=0 |
| F04 | JPEG, normal quality | 8 | 8/8 | 8 | {'REVIEW_REQUIRED': 8} multi-doc-flagged=0 |
| F07 | Page rotated 90° | 2 | 1/2 | 2 | {'REVIEW_REQUIRED': 2} multi-doc-flagged=0 |
| F09 | Skewed 3° | 2 | 2/2 | 2 | {'REVIEW_REQUIRED': 2} multi-doc-flagged=0 |
| F11 | Phone-photo style | 8 | 8/8 | 8 | {'REVIEW_REQUIRED': 8} multi-doc-flagged=0 |
| F12 | Certificate + unrelated second page | 4 | 4/4 | 4 | {'REVIEW_REQUIRED': 4} multi-doc-flagged=0 |
| F13 | Two different certificates in one PDF (page 2 = 납세증명서) | 4 | 2/4 | 4 | {'READY': 1, 'REVIEW_REQUIRED': 3} multi-doc-flagged=0 |
| F16 | Truncated PDF, 0-byte file, PNG disguised as .pdf | 6 | 0/0 | 0 | {'None': 6} multi-doc-flagged=0 |

### Corrupt files

| File | Outcome |
|---|---|
| F16a_사업자등록증_손상.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16b_사업자등록증_빈파일.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16c_사업자등록증_확장자위장.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16a_재학증명서_손상.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16b_재학증명서_빈파일.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16c_재학증명서_확장자위장.pdf | REJECTED_AT_UPLOAD (400) OK |
