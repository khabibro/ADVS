# S1 proj report (scorer v2)

- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; manifest SHA-256 `e650a96d2b4d441bb3b1647e08afaf04840ebc26dc5d0333ca8c8477aef35f67`
- Corpus `dev`, git `bf0106c`, strategy `S1`, project values `True`

## 1. Submission status per set × version

| Set | Version | Expected | Actual | Result | Notes |
|---|---|---|---|---|---|
| B01 | digital | READY | READY | MATCH |   |
| B01 | scanned | (digital expectation) READY | READY | MATCH |   |
| B01 | images | (digital expectation) READY | READY | MATCH |   |
| B02 | digital | READY | READY | MATCH |   |
| B02 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  REQUIRED_FIELD_UNRESOLVED |
| B02 | images | (digital expectation) READY | READY | MATCH |   |
| B03 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  COMPANY_NAME_MISMATCH, INFORMATION_MISMATCH |
| B03 | scanned | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  COMPANY_NAME_MISMATCH, INFORMATION_MISMATCH |
| B03 | images | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  COMPANY_NAME_MISMATCH, INFORMATION_MISMATCH |
| B04 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  INFORMATION_MISMATCH |
| B04 | scanned | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  INFORMATION_MISMATCH |
| B04 | images | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  INFORMATION_MISMATCH |
| B05 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  EXPIRED_DOCUMENT |
| B05 | scanned | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  EXPIRED_DOCUMENT, OCR_UNCERTAIN |
| B05 | images | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  EXPIRED_DOCUMENT |
| B06 | digital | READY (if expiry is inclusive) — record actual | READY | RECORD |   |
| B06 | scanned | (digital expectation) READY (if expiry is inclusive) — record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| B06 | images | (digital expectation) READY (if expiry is inclusive) — record actual | READY | RECORD |   |
| B07 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B07 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B07 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B07 | digital_partial_checklist | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B08 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT |
| B08 | scanned | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT |
| B08 | images | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT |
| B09 | digital | record actual | READY | RECORD | duplicate notice visible=True  |
| B09 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| B09 | images | (digital expectation) record actual | READY | RECORD |   |
| B10 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED |
| B10 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED |
| B10 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED |
| B11 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B12 | digital | NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW |
| B12 | scanned | (digital expectation) NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW |
| B12 | images | (digital expectation) NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW |
| S01 | digital | READY | READY | MATCH |   |
| S01 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S01 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S02 | digital | NEEDS_CORRECTION | READY | MISMATCH | FALSE-READY  |
| S02 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S02 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S03 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  RULE_CONDITION_NOT_MET |
| S03 | scanned | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  OCR_UNCERTAIN, RULE_CONDITION_NOT_MET |
| S03 | images | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  OCR_UNCERTAIN, RULE_CONDITION_NOT_MET |
| S04 | digital | record actual (scale handling) | READY | RECORD |   |
| S04 | scanned | (digital expectation) record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S04 | images | (digital expectation) record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S05 | digital | record actual | NEEDS_CORRECTION | RECORD |  APPLICANT_NAME_MISMATCH |
| S05 | scanned | (digital expectation) record actual | NEEDS_CORRECTION | RECORD |  APPLICANT_NAME_MISMATCH, OCR_UNCERTAIN |
| S05 | images | (digital expectation) record actual | NEEDS_CORRECTION | RECORD |  APPLICANT_NAME_MISMATCH, OCR_UNCERTAIN |
| S06 | digital | record actual | READY | RECORD |   |
| S06 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S06 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S07 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S08 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| S08 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S08 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | digital | REVIEW_REQUIRED | READY | MISMATCH | FALSE-READY  |
| S09 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S10 | digital | READY | READY | MATCH |   |
| S10 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S10 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |

Status totals: {"digital": {"MATCH": 15, "RECORD": 6, "MISMATCH": 2}, "scanned": {"MATCH": 12, "CONSERVATIVE": 4, "RECORD": 6}, "images": {"MATCH": 13, "RECORD": 6, "CONSERVATIVE": 3}}

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
| scanned | 228 | 0 | 12 | 240 | 195 | 195 | 195 | 0 | 81.2% |
| images | 230 | 0 | 10 | 240 | 200 | 200 | 200 | 0 | 83.3% |

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

- False READY: **2** ['S02/digital', 'S09/digital']
- Effective (acted-on) values that are WRONG: []
- READY on RECORD rows (digital): ['B06/digital', 'B06/images', 'B09/digital', 'B09/images', 'S04/digital', 'S06/digital']
- Duplicate-notice expectation: ['B09: visible=True']

## 5. Review burden and automatic decisions

| Version | needs-human fields / submission (mean) | total | all-flagged / submission (v1 style) | auto-decided submissions | of which equal to digital expectation |
|---|---|---|---|---|---|
| digital | 0.91 | 20 | 1.95 | 0/0 | 0 |
| scanned | 2.77 | 61 | 5.23 | 7/22 | 6 |
| images | 2.55 | 56 | 4.59 | 10/22 | 7 |

## 6. Processing time per document (ms)

| Version | Mean | Max |
|---|---|---|
| digital | 29.5 | 102.4 |
| scanned | 24.2 | 57.0 |
| images | 29.8 | 63.7 |

## 7. Format sets

| Set | Title | Files | Classification MATCH/scored | Processed | Document statuses |
|---|---|---|---|---|---|
