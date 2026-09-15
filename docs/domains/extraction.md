# Extraction Domain

Extraction is separate from OCR, normalization, and validation. Each of the four MVP document types has its own extractor (`BaseDocumentExtractor` subclass in `document_intelligence/extraction/`), dispatched through `ExtractorRegistry`. `UNKNOWN` has no extractor -- `registry.extract(UNKNOWN, text)` returns `[]` rather than guessing.

| Document type | Fields (`EXPECTED_FIELDS`) | Method | Limitations |
|---|---|---|---|
| GRADUATION_CERTIFICATE | applicant_name, university_name, department, degree, graduation_date, issue_date | Label-proximity match (성명/이름/신청인, 대학교/대학명/학교명, 학과/전공, 학위, 졸업일자, 발급일자) + date normalization | graduation_date and issue_date use distinct labels (Phase 1A bug: both received the same "first date found anywhere" value) |
| CAREER_CERTIFICATE | applicant_name, company_name, position, employment_start_date, employment_end_date, issue_date | Explicit 입사일/퇴사일 labels first; falls back to splitting a 재직기간/근무기간 "start ~ end" range | **Single employment period only** -- a document listing multiple non-contiguous periods will only surface the first one found, never silently merged |
| BUSINESS_REGISTRATION_CERTIFICATE | company_name, representative_name, business_registration_number, business_address, business_type, business_item, issue_date | Label-proximity match; business number is only searched for *within the text following a business-number label* (사업자등록번호/등록번호), never scanned blindly across the whole document | issue_date is mapped from 개업연월일 (business opening date) since the schema has only one date slot for this type |
| SME_CONFIRMATION_CERTIFICATE | company_name, representative_name, business_registration_number, certificate_number, issue_date, expiration_date, validity_period | Same label-proximity approach; 유효기간 range is split on `~`/`-`/부터 into validity_period (raw range, lightly trimmed) and expiration_date (end of range, or the whole value if not a range) | Range splitting is a simple separator search, not a full date-range parser |

**Provenance** (`ExtractedValue`/`ExtractedField`): `raw_value`, `normalized_value`, `confidence` (heuristic, not calibrated -- 0.9 for a business number match, 0.7 for a label match, 0.55 for a date, never a fabricated precise value), `needs_review`, `extraction_method` (`label_match` / `regex_date` / `regex_date_range` / `regex_business_number`), `source_text` (the exact matched substring, not the surrounding document). A field that cannot be extracted confidently is `None` with `needs_review = True` -- **never a guessed value**.

Business number false-positive resistance: an unrelated 10-digit run elsewhere in the document (e.g. a phone number) is never mistaken for a business registration number, because extraction only looks at text following a recognized label.

Normalization (dates, business numbers, conservative text trim) lives in `document_intelligence/normalization/field_normalizer.py`, a separate module reused by both extraction and validation -- see `docs/domains/validation.md`.
