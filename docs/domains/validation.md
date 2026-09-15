# Validation Rules

`ValidationEngine` (`document_intelligence/validation/engine.py`, `engine_version = "heuristic-v2"`) answers "does this document satisfy submission requirements?" -- a separate question from classification/extraction's "what is this and what values are present?".

Supported rule types (`RuleType`): `REQUIRED_DOCUMENT`, `REQUIRED_FIELD`, `DATE_NOT_EXPIRED`, `ISSUE_DATE_MAX_AGE`, `APPLICANT_NAME_MATCH`, `COMPANY_NAME_MATCH`, `BUSINESS_REGISTRATION_NUMBER_MATCH`, `DUPLICATE_DOCUMENT`, `EXPECTED_DOCUMENT_TYPE`, `CUSTOM_TEXT_RULE`.

**Always-on checks** (independent of any checklist): `EXPECTED_DOCUMENT_TYPE` (if the caller supplied an expected type), `DUPLICATE_DOCUMENT` (same checksum already in the submission), `APPLICANT_NAME_MATCH`/`COMPANY_NAME_MATCH` (against the project's recorded name, when both are present), and `DATE_NOT_EXPIRED` on `expiration_date` whenever that field was extracted -- an expired document is invalid regardless of whether an admin configured a rule for it.

**Database-configured rules**: `DocumentRequirement`/`ValidationRule` rows (already in the schema, keyed by checklist + document_type) are loaded per document and passed to the engine as `ConfiguredRule(rule_type, severity, params)`. The engine owns *how* each rule_type is evaluated; the database decides *whether* it applies and with what parameters:

```
document_type = SME_CONFIRMATION_CERTIFICATE
field = expiration_date
rule_type = DATE_NOT_EXPIRED
severity = ERROR
```

`REQUIRED_FIELD` with `params={}` checks every extracted field; with `params={"field": "issue_date"}` checks only that one. `ISSUE_DATE_MAX_AGE` takes `{"field": ..., "max_age_days": ...}`. `CUSTOM_TEXT_RULE` takes `{"field": ..., "contains": ...}` or `{"field": ..., "equals": ...}`. `BUSINESS_REGISTRATION_NUMBER_MATCH` compares the extracted number against `{"expected_value": ...}` -- if no expected value is configured it is skipped rather than guessed. When no checklist/requirement matches a document at all, the engine falls back to the MVP default of flagging every uncertain/missing field as `REQUIRED_FIELD`/WARNING.

`REQUIRED_DOCUMENT` is evaluated separately at the *submission* level (`ValidationEngine.validate_required_documents`, used by `POST /projects/{id}/verify`), since a single document's validation cannot know whether a sibling document type is missing from the submission.

Each `ValidationIssue` carries rule_type, pass/fail, severity, expected/actual value, message, code. Overall status:

- **READY** -- all evaluated checks passed; this only means the pre-check found no clear configured problem
- **REVIEW_REQUIRED** -- no failed ERROR, but at least one failed WARNING (uncertain OCR/missing field, duplicate upload) -- uncertainty is never silently converted into READY
- **NEEDS_CORRECTION** -- at least one failed ERROR (wrong document type, name mismatch, expired document, a configured rule at ERROR severity)

`comparable()` normalizes whitespace/punctuation/case before any text comparison. `GET /documents/{id}` returns the computed `overall_status`; it is not a stored column.
