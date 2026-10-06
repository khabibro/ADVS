# B2-D2 dev report (scorer v2)

- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; manifest SHA-256 `e650a96d2b4d441bb3b1647e08afaf04840ebc26dc5d0333ca8c8477aef35f67`
- Corpus `dev`, git `c76dc19`, strategy `None`, project values `False`

## 1. Submission status per set × version

| Set | Version | Expected | Actual | Result | Notes |
|---|---|---|---|---|---|
| B01 | digital | READY | READY | MATCH |   |
| B01 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B01 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B02 | digital | READY | READY | MATCH |   |
| B02 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B02 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B03 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  INFORMATION_MISMATCH |
| B03 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B03 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B04 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  INFORMATION_MISMATCH |
| B04 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B04 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B05 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  EXPIRED_DOCUMENT |
| B05 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B05 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B06 | digital | READY (if expiry is inclusive) — record actual | READY | RECORD |   |
| B06 | scanned | (digital expectation) READY (if expiry is inclusive) — record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| B06 | images | (digital expectation) READY (if expiry is inclusive) — record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| B07 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B07 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | digital_partial_checklist | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B08 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT |
| B08 | scanned | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT, OCR_UNCERTAIN |
| B08 | images | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT, OCR_UNCERTAIN |
| B09 | digital | record actual | READY | RECORD | duplicate notice visible=True  |
| B09 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| B09 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| B10 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED |
| B10 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED, OCR_UNCERTAIN |
| B10 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED, OCR_UNCERTAIN |
| B11 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B12 | digital | NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW |
| B12 | scanned | (digital expectation) NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW, OCR_UNCERTAIN |
| B12 | images | (digital expectation) NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW, OCR_UNCERTAIN |
| S01 | digital | READY | READY | MATCH |   |
| S01 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S01 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S02 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  RULE_CONDITION_NOT_MET |
| S02 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  CLASSIFICATION_REQUIRES_REVIEW, OCR_UNCERTAIN |
| S02 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S03 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  RULE_CONDITION_NOT_MET |
| S03 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S03 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S04 | digital | record actual (scale handling) | READY | RECORD |   |
| S04 | scanned | (digital expectation) record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S04 | images | (digital expectation) record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S05 | digital | record actual | NEEDS_CORRECTION | RECORD |  INFORMATION_MISMATCH |
| S05 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S05 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S06 | digital | record actual | READY | RECORD |   |
| S06 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  CLASSIFICATION_REQUIRES_REVIEW, OCR_UNCERTAIN |
| S06 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S07 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S08 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| S08 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S08 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| S09 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S10 | digital | READY | READY | MATCH |   |
| S10 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S10 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |

Status totals: {"digital": {"MATCH": 17, "RECORD": 6}, "scanned": {"CONSERVATIVE": 9, "RECORD": 6, "MATCH": 7}, "images": {"CONSERVATIVE": 9, "RECORD": 6, "MATCH": 7}}

## 2. Classification

| Type | Version | Match / total | Mismatch |
|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | digital | 12/12 | 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | images | 12/12 | 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | scanned | 12/12 | 0 |
| ENROLLMENT_CERTIFICATE | digital | 9/9 | 0 |
| ENROLLMENT_CERTIFICATE | images | 9/9 | 0 |
| ENROLLMENT_CERTIFICATE | scanned | 9/9 | 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | digital | 12/12 | 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | images | 12/12 | 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | scanned | 12/12 | 0 |
| SME_CONFIRMATION_CERTIFICATE | digital | 12/12 | 0 |
| SME_CONFIRMATION_CERTIFICATE | images | 12/12 | 0 |
| SME_CONFIRMATION_CERTIFICATE | scanned | 12/12 | 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | digital | 12/12 | 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | images | 12/12 | 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | scanned | 12/12 | 0 |
| TRANSCRIPT | digital | 9/9 | 0 |
| TRANSCRIPT | images | 9/9 | 0 |
| TRANSCRIPT | scanned | 9/9 | 0 |
| UNKNOWN | digital | 3/3 | 0 |
| UNKNOWN | images | 3/3 | 0 |
| UNKNOWN | scanned | 3/3 | 0 |

## 3. Field outcomes (machine value) and OCR auto-acceptance

| Version | CORRECT | WRONG | UNRESOLVED | of N | acts (effective value) | acts correct | AUTO_ACCEPTED | false auto-accept | auto-accept rate |
|---|---|---|---|---|---|---|---|---|---|
| digital | 240 | 0 | 0 | 240 | 236 | 236 | 0 | 0 | n/a |
| scanned | 228 | 0 | 12 | 240 | 97 | 97 | 97 | 0 | 40.4% |
| images | 230 | 0 | 10 | 240 | 111 | 111 | 111 | 0 | 46.2% |

Absent-field checks (VERIFIED_ABSENT): {"digital": {"NE_CORRECT_ABSTENTION": 3}, "scanned": {"NE_CORRECT_ABSTENTION": 3}, "images": {"NE_CORRECT_ABSTENTION": 3}}

| Type | Version | CORRECT | WRONG | UNRESOLVED | of N |
|---|---|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | digital | 24 | 0 | 0 | 24 |
| BUSINESS_REGISTRATION_CERTIFICATE | images | 24 | 0 | 0 | 24 |
| BUSINESS_REGISTRATION_CERTIFICATE | scanned | 23 | 0 | 1 | 24 |
| ENROLLMENT_CERTIFICATE | digital | 43 | 0 | 0 | 43 |
| ENROLLMENT_CERTIFICATE | images | 41 | 0 | 2 | 43 |
| ENROLLMENT_CERTIFICATE | scanned | 41 | 0 | 2 | 43 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | digital | 36 | 0 | 0 | 36 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | images | 36 | 0 | 0 | 36 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | scanned | 36 | 0 | 0 | 36 |
| SME_CONFIRMATION_CERTIFICATE | digital | 48 | 0 | 0 | 48 |
| SME_CONFIRMATION_CERTIFICATE | images | 48 | 0 | 0 | 48 |
| SME_CONFIRMATION_CERTIFICATE | scanned | 48 | 0 | 0 | 48 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | digital | 35 | 0 | 0 | 35 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | images | 35 | 0 | 0 | 35 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | scanned | 35 | 0 | 0 | 35 |
| TRANSCRIPT | digital | 54 | 0 | 0 | 54 |
| TRANSCRIPT | images | 46 | 0 | 8 | 54 |
| TRANSCRIPT | scanned | 45 | 0 | 9 | 54 |

## 4. Safety

- False READY: **0** []
- Effective (acted-on) values that are WRONG: []
- READY on RECORD rows (digital): ['B06/digital', 'B09/digital', 'S04/digital', 'S06/digital']
- Duplicate-notice expectation: ['B09: visible=True']

## 5. Review burden and automatic decisions

| Version | needs-human fields / submission (mean) | total | all-flagged / submission (v1 style) | auto-decided submissions | of which equal to digital expectation |
|---|---|---|---|---|---|
| digital | 0.91 | 20 | 1.95 | 0/0 | 0 |
| scanned | 7.23 | 159 | 5.23 | 1/22 | 1 |
| images | 6.59 | 145 | 4.59 | 1/22 | 1 |

## 6. Processing time per document (ms)

| Version | Mean | Max |
|---|---|---|
| digital | 37.4 | 82.4 |
| scanned | 32.0 | 50.4 |
| images | 39.2 | 69.3 |

## 7. Format sets

| Set | Title | Files | Classification MATCH/scored | Processed | Document statuses |
|---|---|---|---|---|---|
| F01 | Digital PDF with text layer | 8 | 8/8 | 8 | {'READY': 7, 'REVIEW_REQUIRED': 1} multi-doc-flagged=0 |
| F02 | Scanned PDF (image only, 200 DPI) | 8 | 8/8 | 8 | {'READY': 1, 'REVIEW_REQUIRED': 7} multi-doc-flagged=0 |
| F03 | PNG image | 8 | 8/8 | 8 | {'READY': 1, 'REVIEW_REQUIRED': 7} multi-doc-flagged=0 |
| F04 | JPEG, normal quality | 8 | 8/8 | 8 | {'READY': 1, 'REVIEW_REQUIRED': 7} multi-doc-flagged=0 |
| F05 | JPEG, heavy compression (quality 30) | 8 | 8/8 | 8 | {'READY': 1, 'REVIEW_REQUIRED': 7} multi-doc-flagged=0 |
| F06 | WEBP image | 8 | 8/8 | 8 | {'READY': 1, 'REVIEW_REQUIRED': 7} multi-doc-flagged=0 |
| F07 | Page rotated 90° | 2 | 1/2 | 2 | {'REVIEW_REQUIRED': 2} multi-doc-flagged=0 |
| F08 | EXIF orientation tags (correct and wrong) | 4 | 4/4 | 4 | {'REVIEW_REQUIRED': 4} multi-doc-flagged=0 |
| F09 | Skewed 3° | 2 | 2/2 | 2 | {'REVIEW_REQUIRED': 2} multi-doc-flagged=0 |
| F10 | Low resolution (~100 DPI) | 4 | 4/4 | 4 | {'REVIEW_REQUIRED': 4} multi-doc-flagged=0 |
| F11 | Phone-photo style | 8 | 8/8 | 8 | {'READY': 1, 'REVIEW_REQUIRED': 7} multi-doc-flagged=0 |
| F12 | Certificate + unrelated second page | 4 | 4/4 | 4 | {'READY': 3, 'REVIEW_REQUIRED': 1} multi-doc-flagged=0 |
| F13 | Two different certificates in one PDF (page 2 = 납세증명서) | 4 | 4/4 | 4 | {'REVIEW_REQUIRED': 4} multi-doc-flagged=4 |
| F14 | Certificate + blank page | 4 | 4/4 | 4 | {'READY': 3, 'REVIEW_REQUIRED': 1} multi-doc-flagged=0 |
| F15 | TIFF, BMP and DOCX | 6 | 0/6 | 0 | {'None': 6} multi-doc-flagged=0 |
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
