# B1 report — ADVS test-variant corpus

- Scorer: `evaluation/harness/score_variants.py` SHA-256 `b0ae22b51227401144787757910d1adc7b14266933d30838d06ada4706fd8c59`
- Harness: `evaluation/harness/run_variants.py` SHA-256 `d6c2e82e98307571c3640a01ae6e32ad5d39b6ce917ff4ae21bd0dad73e3ed21`
- Manifest SHA-256 `e650a96d2b4d441bb3b1647e08afaf04840ebc26dc5d0333ca8c8477aef35f67`
- Git HEAD at run: `e77cf4b`; submission date fixed to the manifest value.

## Scoring rules

```
-----------------------------------------------
Classification
    predicted document type == manifest `expected_classification`.
    Files whose expectation is "n/a" (corrupt-file set F16) are not scored.

Fields (only for KNOWN_VALUE / VERIFIED_ABSENT manifest entries of files whose
expected_classification is a supported type; fields of expected-UNKNOWN files
are not scored)
    System value is the field's effective normalized value. Normalization
    before comparing, by field:
      * dates (issue_date, valid_from, valid_until)  -> ISO yyyy-mm-dd string
      * business_registration_number                 -> its 10 digits
      * gpa                                          -> number, 2 decimals
      * gpa_scale                                    -> number as 4.5 / 4.3
      * everything else (names, text)                -> whitespace collapsed
        ONLY (no case folding, no punctuation or legal-entity stripping)
    Outcome:
      CORRECT     equal
      WRONG       non-null value that differs (the dangerous case)
      UNRESOLVED  null / abstained
      NOT_EVALUATED  manifest state VERIFIED_ABSENT, counted separately:
                  CORRECT_ABSTENTION if the system produced no value,
                  WRONG if it produced one.
    Values are scored on the extractor's own machine value (`normalized_value`),
    so OCR extraction quality is visible even though OCR fields are always
    gated to human review. A field is "flagged" when the system will not act
    on it without a human (no effective value, or needs_review). WRONG is split
    by that: an UNFLAGGED wrong value (the system would act on it) is the
    dangerous case. The harness also records the effective (policy-gated) value;
    the report adds "trusted correct" = CORRECT and unflagged.

Submission status
    actual vs expected[version].submission_status. An expected string that
    contains "record actual" or the word "or" is RECORD (reported, not
    scored). Otherwise the leading status token must equal the actual status.
    B07 `digital_partial_checklist` is scored against B07's digital
    expectation.

False READY
    The submission returned READY where the expected status is not READY, or
    where the version is scanned/images (OCR policy: never READY without human
    confirmation). READY on a RECORD row of a digital version is listed
    separately as READY_ON_RECORD for manual judgement.

Review burden
    Number of extracted fields with needs_review=True per submission, split
    into fields with a value (confirm) and fields without one (supply).
```

## 1. Submission status per set × version

| Set | Version | Expected | Actual | Result | Issue codes |
|---|---|---|---|---|---|
| B01 | digital | READY | READY | MATCH |  |
| B01 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B01 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B02 | digital | READY | READY | MATCH |  |
| B02 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B02 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B03 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH | INFORMATION_MISMATCH |
| B03 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B03 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B04 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH | INFORMATION_MISMATCH |
| B04 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B04 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| B05 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH | EXPIRED_DOCUMENT |
| B05 | scanned | REVIEW_REQUIRED or NEEDS_CORRECTION — record actual | REVIEW_REQUIRED | RECORD | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B05 | images | REVIEW_REQUIRED or NEEDS_CORRECTION — record actual | REVIEW_REQUIRED | RECORD | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B06 | digital | READY (if expiry is inclusive) — record actual | READY | RECORD |  |
| B06 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B06 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | REQUIRED_FIELD_UNRESOLVED |
| B07 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B07 | digital_partial_checklist | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | REQUIRED_FIELD_UNRESOLVED |
| B08 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH | MISSING_REQUIRED_DOCUMENT |
| B08 | scanned | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH | MISSING_REQUIRED_DOCUMENT, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B08 | images | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH | MISSING_REQUIRED_DOCUMENT, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B09 | digital | record actual | READY | RECORD |  |
| B09 | scanned | record actual | REVIEW_REQUIRED | RECORD | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B09 | images | record actual | REVIEW_REQUIRED | RECORD | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B10 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | BUSINESS_NUMBER_CHECKSUM_FAILED |
| B10 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | BUSINESS_NUMBER_CHECKSUM_FAILED, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B10 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | BUSINESS_NUMBER_CHECKSUM_FAILED, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B11 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH | UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | scanned | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED, UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B11 | images | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED, UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| B12 | digital | NEEDS_CORRECTION or REVIEW_REQUIRED — record actual | REVIEW_REQUIRED | RECORD | MULTIPLE_DOCUMENTS_REQUIRE_REVIEW |
| B12 | scanned | REVIEW_REQUIRED or NEEDS_CORRECTION — record actual | REVIEW_REQUIRED | RECORD | MULTIPLE_DOCUMENTS_REQUIRE_REVIEW, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| B12 | images | REVIEW_REQUIRED or NEEDS_CORRECTION — record actual | REVIEW_REQUIRED | RECORD | MULTIPLE_DOCUMENTS_REQUIRE_REVIEW, OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S01 | digital | READY | REVIEW_REQUIRED | MISMATCH | OCR_UNCERTAIN |
| S01 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S01 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S02 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH | OCR_UNCERTAIN |
| S02 | scanned | REVIEW_REQUIRED or NEEDS_CORRECTION — record actual | REVIEW_REQUIRED | RECORD | UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S02 | images | REVIEW_REQUIRED or NEEDS_CORRECTION — record actual | REVIEW_REQUIRED | RECORD | OCR_UNCERTAIN |
| S03 | digital | NEEDS_CORRECTION | NEEDS_CORRECTION | MATCH | OCR_UNCERTAIN, RULE_CONDITION_NOT_MET |
| S03 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S03 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S04 | digital | record actual (scale handling) | REVIEW_REQUIRED | RECORD | OCR_UNCERTAIN |
| S04 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S04 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S05 | digital | record actual | REVIEW_REQUIRED | RECORD | OCR_UNCERTAIN |
| S05 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S05 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S06 | digital | record actual | REVIEW_REQUIRED | RECORD | OCR_UNCERTAIN |
| S06 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S06 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S07 | digital | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH | UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | scanned | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH | UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S07 | images | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH | UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW |
| S08 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S08 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S08 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | digital | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S09 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S09 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN, REQUIRED_FIELD_UNRESOLVED |
| S10 | digital | READY | REVIEW_REQUIRED | MISMATCH | OCR_UNCERTAIN |
| S10 | scanned | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |
| S10 | images | REVIEW_REQUIRED | REVIEW_REQUIRED | MATCH | OCR_UNCERTAIN |

Totals: {'MATCH': 44, 'RECORD': 14, 'MISMATCH': 9}

## 2. Classification accuracy per document type × version

| Type | Version | Match / total | Mismatch | Not processed |
|---|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | digital | 12/12 | 0 | 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | images | 12/12 | 0 | 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | scanned | 12/12 | 0 | 0 |
| ENROLLMENT_CERTIFICATE | digital | 9/9 | 0 | 0 |
| ENROLLMENT_CERTIFICATE | images | 9/9 | 0 | 0 |
| ENROLLMENT_CERTIFICATE | scanned | 7/9 | 2 | 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | digital | 12/12 | 0 | 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | images | 12/12 | 0 | 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | scanned | 12/12 | 0 | 0 |
| SME_CONFIRMATION_CERTIFICATE | digital | 12/12 | 0 | 0 |
| SME_CONFIRMATION_CERTIFICATE | images | 12/12 | 0 | 0 |
| SME_CONFIRMATION_CERTIFICATE | scanned | 12/12 | 0 | 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | digital | 12/12 | 0 | 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | images | 12/12 | 0 | 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | scanned | 12/12 | 0 | 0 |
| TRANSCRIPT | digital | 9/9 | 0 | 0 |
| TRANSCRIPT | images | 6/9 | 3 | 0 |
| TRANSCRIPT | scanned | 1/9 | 8 | 0 |
| UNKNOWN | digital | 3/3 | 0 | 0 |
| UNKNOWN | images | 3/3 | 0 | 0 |
| UNKNOWN | scanned | 3/3 | 0 | 0 |

## 3. Field outcomes per document type × version

Denominator = evaluated KNOWN_VALUE fields. NOT_EVALUATED (VERIFIED_ABSENT) counted separately.

| Type | Version | CORRECT | WRONG | UNRESOLVED | of N | Absent: correct abstention / WRONG |
|---|---|---|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | digital | 24 | 0 | 0 | 24 | 0 / 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | images | 12 | 12 | 0 | 24 | 0 / 0 |
| BUSINESS_REGISTRATION_CERTIFICATE | scanned | 12 | 7 | 5 | 24 | 0 / 0 |
| ENROLLMENT_CERTIFICATE | digital | 43 | 0 | 0 | 43 | 2 / 0 |
| ENROLLMENT_CERTIFICATE | images | 40 | 1 | 2 | 43 | 2 / 0 |
| ENROLLMENT_CERTIFICATE | scanned | 28 | 3 | 12 | 43 | 2 / 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | digital | 35 | 1 | 0 | 36 | 0 / 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | images | 19 | 11 | 6 | 36 | 0 / 0 |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | scanned | 22 | 4 | 10 | 36 | 0 / 0 |
| SME_CONFIRMATION_CERTIFICATE | digital | 48 | 0 | 0 | 48 | 0 / 0 |
| SME_CONFIRMATION_CERTIFICATE | images | 48 | 0 | 0 | 48 | 0 / 0 |
| SME_CONFIRMATION_CERTIFICATE | scanned | 37 | 1 | 10 | 48 | 0 / 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | digital | 35 | 0 | 0 | 35 | 1 / 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | images | 24 | 2 | 9 | 35 | 1 / 0 |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | scanned | 23 | 0 | 12 | 35 | 1 / 0 |
| TRANSCRIPT | digital | 54 | 0 | 0 | 54 | 0 / 0 |
| TRANSCRIPT | images | 31 | 0 | 23 | 54 | 0 / 0 |
| TRANSCRIPT | scanned | 5 | 0 | 49 | 54 | 0 / 0 |

| Version | CORRECT | WRONG | UNRESOLVED | of N | WRONG unflagged | CORRECT and trusted (no review needed) | Absent: abstained / WRONG |
|---|---|---|---|---|---|---|---|
| digital | 239 | 1 | 0 | 240 | 1 | 218 | 3 / 0 |
| scanned | 127 | 15 | 98 | 240 | 0 | 0 | 3 / 0 |
| images | 174 | 26 | 40 | 240 | 0 | 0 | 3 / 0 |

WRONG results on an EXPECTATION_DISPUTED field (counted in WRONG above): {'digital': 1}
- B02-3_납세증명서.pdf / company_name: WRONG ('(주)테스트상사') — manifest value uses the compatibility character U+3231 (㈜); the system folds it to the canonical '(주)' by Unicode NFKC at extraction. Same text, different code points.

## 4. False READY

- False READY count: **0** []
- READY on RECORD rows (digital, manual judgement): ['B06/digital', 'B09/digital']

## 5. Review burden (fields needing human confirmation per submission)

| Version | Mean per submission | Total |
|---|---|---|
| digital | 3.3 | 72 |
| scanned | 5.9 | 130 |
| images | 4.9 | 108 |

## 6. Processing time per document (ms)

| Version | Mean | Max |
|---|---|---|
| digital | 29.5 | 59.8 |
| scanned | 11490.1 | 26152.8 |
| images | 8993.0 | 22513.1 |

## 7. Format sets

| Set | Title | Files | Classification MATCH/scored | Processed | Doc statuses | Notes |
|---|---|---|---|---|---|---|
| F01 | Digital PDF with text layer | 8 | 8/8 | 8 | {'READY': 4, 'REVIEW_REQUIRED': 4} | uploads rejected: 0 |
| F02 | Scanned PDF (image only, 200 DPI) | 8 | 7/8 | 8 | {'REVIEW_REQUIRED': 8} | uploads rejected: 0 |
| F03 | PNG image | 8 | 7/8 | 8 | {'REVIEW_REQUIRED': 8} | uploads rejected: 0 |
| F04 | JPEG, normal quality | 8 | 7/8 | 8 | {'REVIEW_REQUIRED': 8} | uploads rejected: 0 |
| F05 | JPEG, heavy compression (quality 30) | 8 | 8/8 | 8 | {'REVIEW_REQUIRED': 8} | uploads rejected: 0 |
| F06 | WEBP image | 8 | 6/8 | 8 | {'REVIEW_REQUIRED': 8} | uploads rejected: 0 |
| F07 | Page rotated 90° | 2 | 1/2 | 2 | {'REVIEW_REQUIRED': 2} | uploads rejected: 0 |
| F08 | EXIF orientation tags (correct and wrong) | 4 | 3/4 | 4 | {'REVIEW_REQUIRED': 4} | uploads rejected: 0 |
| F09 | Skewed 3° | 2 | 2/2 | 2 | {'REVIEW_REQUIRED': 2} | uploads rejected: 0 |
| F10 | Low resolution (~100 DPI) | 4 | 4/4 | 4 | {'REVIEW_REQUIRED': 4} | uploads rejected: 0 |
| F11 | Phone-photo style | 8 | 6/8 | 8 | {'REVIEW_REQUIRED': 8} | uploads rejected: 0 |
| F12 | Certificate + unrelated second page | 4 | 3/4 | 4 | {'READY': 1, 'REVIEW_REQUIRED': 3} | uploads rejected: 0 |
| F13 | Two different certificates in one PDF (page 2 = 납세증명서) | 4 | 4/4 | 4 | {'READY': 1, 'REVIEW_REQUIRED': 3} | uploads rejected: 0 |
| F14 | Certificate + blank page | 4 | 3/4 | 4 | {'READY': 1, 'REVIEW_REQUIRED': 3} | uploads rejected: 0 |
| F15 | TIFF, BMP and DOCX | 6 | 0/6 | 0 | {'None': 6} | uploads rejected: 6 |
| F16 | Truncated PDF, 0-byte file, PNG disguised as .pdf | 6 | 0/0 | 0 | {'None': 6} | uploads rejected: 6 |

### F16 corrupt files

| File | Outcome |
|---|---|
| F16a_사업자등록증_손상.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16b_사업자등록증_빈파일.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16c_사업자등록증_확장자위장.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16a_재학증명서_손상.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16b_재학증명서_빈파일.pdf | REJECTED_AT_UPLOAD (400) OK |
| F16c_재학증명서_확장자위장.pdf | REJECTED_AT_UPLOAD (400) OK |
