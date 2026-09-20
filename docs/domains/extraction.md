# Extraction Domain

Extraction is separate from OCR, normalization, and validation. Each supported document type has its own extractor (`BaseDocumentExtractor` subclass in `document_intelligence/extraction/`), dispatched through `ExtractorRegistry`. `UNKNOWN` has no extractor -- `registry.extract(UNKNOWN, text)` returns `[]` rather than guessing.

| Document type | Fields (`EXPECTED_FIELDS`) | Method | Limitations |
|---|---|---|---|
| GRADUATION_CERTIFICATE | applicant_name, university_name, department, degree, graduation_date, issue_date | Label-proximity match (성명/이름/신청인, 대학교/대학명/학교명, 학과/전공, 학위, 졸업일자, 발급일자) + date normalization | graduation_date and issue_date use distinct labels (Phase 1A bug: both received the same "first date found anywhere" value) |
| CAREER_CERTIFICATE | applicant_name, company_name, position, employment_start_date, employment_end_date, issue_date | Explicit 입사일/퇴사일 labels first; falls back to splitting a 재직기간/근무기간 "start ~ end" range | **Single employment period only** -- a document listing multiple non-contiguous periods will only surface the first one found, never silently merged |
| BUSINESS_REGISTRATION_CERTIFICATE | company_name, representative_name, business_registration_number, business_address, business_type, business_item, issue_date | Label-proximity match; business number is only searched for *within the text following a business-number label* (사업자등록번호/등록번호), never scanned blindly across the whole document | issue_date is mapped from 개업연월일 (business opening date) since the schema has only one date slot for this type |
| SME_CONFIRMATION_CERTIFICATE | company_name, representative_name, business_registration_number, certificate_number, issue_date, valid_from, valid_until | Same label-proximity approach; 유효기간 is split into canonical ISO start/end dates | Range splitting is a simple separator search, not a full date-range parser |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | company_name, business_registration_number, issue_date, valid_until | Conservative label-proximity extraction | Exact layouts still require mentor samples |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | workplace_name, business_registration_number, issue_date, valid_until | Conservative label-proximity extraction | `workplace_name` is not treated as equivalent to `company_name` |
| ENROLLMENT_CERTIFICATE | student_name, university_name, department, student_id, issue_date | Conservative label-proximity extraction | No issue-date decision is made here |
| TRANSCRIPT | student_name, university_name, student_id, issue_date, gpa, gpa_scale | GPA numerator/scale become numeric-compatible decimal strings while raw text is retained | Courses and grade history are out of scope |

**Provenance** (`ExtractedValue`/`ExtractedField`): `raw_value`, `normalized_value`, `confidence` (heuristic, not calibrated -- 0.9 for a business number match, 0.7 for a label match, 0.55 for a date, never a fabricated precise value), `needs_review`, `extraction_method` (`label_match` / `regex_date` / `regex_date_range` / `regex_business_number`), `source_text` (the exact matched substring, not the surrounding document). A field that cannot be extracted confidently is `None` with `needs_review = True` -- **never a guessed value**.

Business number false-positive resistance: an unrelated 10-digit run elsewhere in the document (e.g. a phone number) is never mistaken for a business registration number, because extraction only looks at text following a recognized label. Recognized values normalize to ten digits for future deterministic comparison while preserving the formatted `raw_value`.

Normalization (dates, business numbers, GPA, conservative text trim) lives in `document_intelligence/normalization/field_normalizer.py`. Organization names only receive whitespace/edge-punctuation cleanup. Extraction does not perform cross-document matching, generalized expiry decisions, issue-date rules, or GPA thresholds.
