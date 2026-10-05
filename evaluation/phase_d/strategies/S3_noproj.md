# S3 noproj report (scorer v2)

- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; manifest SHA-256 `e650a96d2b4d441bb3b1647e08afaf04840ebc26dc5d0333ca8c8477aef35f67`
- Corpus `dev`, git `09966c8`, strategy `S3`, project values `False`

## 1. Submission status per set × version

| Set | Version | Expected | Actual | Result | Notes |
|---|---|---|---|---|---|
| B01 | digital | READY | READY | MATCH |   |
| B01 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B01 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B02 | digital | READY | READY | MATCH |   |
| B02 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B02 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B03 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  INFORMATION_MISMATCH |
| B03 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B03 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B04 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  INFORMATION_MISMATCH |
| B04 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B04 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| B05 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  EXPIRED_DOCUMENT |
| B05 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B05 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B06 | digital | READY (if expiry is inclusive) — record actual | READY | RECORD |   |
| B06 | scanned | (digital expectation) READY (if expiry is inclusive) — record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B06 | images | (digital expectation) READY (if expiry is inclusive) — record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B07 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | digital_partial_checklist | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  REQUIRED_FIELD_UNRESOLVED |
| B08 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT |
| B08 | scanned | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B08 | images | (digital expectation) NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  MISSING_REQUIRED_DOCUMENT, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B09 | digital | record actual | READY | RECORD | duplicate notice visible=False  |
| B09 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B09 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B10 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED |
| B10 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B10 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  BUSINESS_NUMBER_CHECKSUM_FAILED, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B11 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED, UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED, UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B12 | digital | NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW |
| B12 | scanned | (digital expectation) NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B12 | images | (digital expectation) NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD |  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S01 | digital | READY | REVIEW_REQUIRED | MISMATCH |  OCR_UNCERTAIN |
| S01 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S01 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S02 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH |  OCR_UNCERTAIN |
| S02 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S02 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S03 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH |  OCR_UNCERTAIN, RULE_CONDITION_NOT_MET |
| S03 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S03 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S04 | digital | record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S04 | scanned | (digital expectation) record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S04 | images | (digital expectation) record actual (scale handling) | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S05 | digital | record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S05 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S05 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S06 | digital | record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S06 | scanned | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S06 | images | (digital expectation) record actual | REVIEW_REQUIRED | RECORD |  OCR_UNCERTAIN |
| S07 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | scanned | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | images | (digital expectation) NEEDS_CORRECTION | REVIEW_REQUIRED | MATCH |  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S08 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S08 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S08 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN |
| S09 | scanned | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | images | (digital expectation) REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH |  OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S10 | digital | READY | REVIEW_REQUIRED | MISMATCH |  OCR_UNCERTAIN |
| S10 | scanned | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |
| S10 | images | (digital expectation) READY | REVIEW_REQUIRED | CONSERVATIVE |  OCR_UNCERTAIN |

Status totals: {"digital": {"MATCH": 14, "RECORD": 6, "MISMATCH": 3}, "scanned": {"CONSERVATIVE": 9, "RECORD": 6, "MATCH": 7}, "images": {"CONSERVATIVE": 9, "RECORD": 6, "MATCH": 7}}

## 2. Classification

| Type | Version | Match / total | Mismatch |
|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | digital | 12/12 | 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | images | 12/12 | 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | scanned | 12/12 | 0 |
| ENROLLMENT_CERTIFICATE | digital | 9/9 | 0 |
| ENROLLMENT_CERTIFICATE | images | 9/9 | 0 |
| ENROLLMENT_CERTIFICATE | scanned | 7/9 | 2 |
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
| TRANSCRIPT | images | 6/9 | 3 |
| TRANSCRIPT | scanned | 1/9 | 8 |
| UNKNOWN | digital | 3/3 | 0 |
| UNKNOWN | images | 3/3 | 0 |
| UNKNOWN | scanned | 3/3 | 0 |

## 3. Field outcomes (machine value) and OCR auto-acceptance

| Version | CORRECT | WRONG | UNRESOLVED | of N | acts (effective value) | acts correct | AUTO_ACCEPTED | false auto-accept | auto-accept rate |
|---|---|---|---|---|---|---|---|---|---|
| digital | 240 | 0 | 0 | 240 | 219 | 219 | 0 | 0 | n/a |
| scanned | 139 | 3 | 98 | 240 | 46 | 46 | 46 | 0 | 19.2% |
| images | 199 | 1 | 40 | 240 | 88 | 88 | 88 | 0 | 36.7% |

Absent-field checks (VERIFIED_ABSENT): {"digital": {"NE_CORRECT_ABSTENTION": 3}, "scanned": {"NE_CORRECT_ABSTENTION": 3}, "images": {"NE_CORRECT_ABSTENTION": 3}}

| Type | Version | CORRECT | WRONG | UNRESOLVED | of N |
|---|---|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | digital | 24 | 0 | 0 | 24 |
| BUSINESS_REGISTRATION_CERTIFICATE | images | 24 | 0 | 0 | 24 |
| BUSINESS_REGISTRATION_CERTIFICATE | scanned | 19 | 0 | 5 | 24 |
| ENROLLMENT_CERTIFICATE | digital | 43 | 0 | 0 | 43 |
| ENROLLMENT_CERTIFICATE | images | 40 | 1 | 2 | 43 |
| ENROLLMENT_CERTIFICATE | scanned | 28 | 3 | 12 | 43 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | digital | 36 | 0 | 0 | 36 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | images | 30 | 0 | 6 | 36 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | scanned | 26 | 0 | 10 | 36 |
| SME_CONFIRMATION_CERTIFICATE | digital | 48 | 0 | 0 | 48 |
| SME_CONFIRMATION_CERTIFICATE | images | 48 | 0 | 0 | 48 |
| SME_CONFIRMATION_CERTIFICATE | scanned | 38 | 0 | 10 | 48 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | digital | 35 | 0 | 0 | 35 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | images | 26 | 0 | 9 | 35 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | scanned | 23 | 0 | 12 | 35 |
| TRANSCRIPT | digital | 54 | 0 | 0 | 54 |
| TRANSCRIPT | images | 31 | 0 | 23 | 54 |
| TRANSCRIPT | scanned | 5 | 0 | 49 | 54 |

## 4. Safety

- False READY: **0** []
- Effective (acted-on) values that are WRONG: []
- READY on RECORD rows (digital): ['B06/digital', 'B09/digital']
- Duplicate-notice expectation: ['B09: visible=False']

## 5. Review burden and automatic decisions

| Version | needs-human fields / submission (mean) | total | all-flagged / submission (v1 style) | auto-decided submissions | of which equal to digital expectation |
|---|---|---|---|---|---|
| digital | 1.68 | 37 | 3.27 | 0/0 | 0 |
| scanned | 9.55 | 210 | 5.91 | 1/22 | 1 |
| images | 7.64 | 168 | 4.91 | 1/22 | 1 |

## 6. Processing time per document (ms)

| Version | Mean | Max |
|---|---|---|
| digital | 25.0 | 51.7 |
| scanned | 19.2 | 30.4 |
| images | 25.6 | 43.9 |

## 7. Format sets

| Set | Title | Files | Classification MATCH/scored | Processed | Document statuses |
|---|---|---|---|---|---|
