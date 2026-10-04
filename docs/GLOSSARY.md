# Glossary

Terms as used in this repository's code, docs, and evaluation reports.
Verified against commit `f1d949f` on `main`. See `docs/ARCHITECTURE.md` for
how these fit together.

## Domain model

**Workflow** — product/API concept for "what a project must submit."
Persisted as a `Checklist` row; there is no separate `Workflow` table.

**Checklist** — the database model backing a Workflow. Has many
`DocumentRequirement` rows (`Checklist.requirements`).

**DocumentRequirement** — one document type a Checklist expects, with a
`required: bool` flag. Has many `ValidationRule` rows.

**ValidationRule** — a configured, parameterized check (`rule_type`,
`severity`, JSON `params`) attached to a `DocumentRequirement`. "How a rule
type behaves" is code (`validation/engine.py`); "whether/with what
parameters it applies" is this row.

**Project** — one applicant's/business's submission effort, linked to at
most one `Checklist` via `checklist_id`.

**Submission** — the set of documents a Project has uploaded for one
verification pass. A Project has many Submissions over time (one `Document`
belongs to exactly one `Submission`).

**Document** — one uploaded file and its processing state
(`processing_status`, `document_type`, `classification_confidence`,
`processing_version`).

**ExtractedField** — one field value pulled from a Document by an
extractor, with `raw_value`, `normalized_value`, `confidence`,
`needs_review`, and `evidence` (a list of evidence references, see below).

**FieldReview** — a human's decision about one `ExtractedField`:
`CONFIRMED`, `CORRECTED`, `REJECTED`, or `CANNOT_DETERMINE`. Exactly one
review may be `is_current = true` per `(document_id, field_name)` pair —
enforced by a partial unique index, not just application logic.

**ValidationResult** — the outcome of one rule check against one document
or project (`passed`, `severity`, `code`, `message`).

**Canonical field name** — the field-name vocabulary in
`EXPECTED_FIELDS`/`SUPPORTED_FIELDS` (`app/core/domain.py`) — e.g.
`company_name`, `gpa`, `valid_until`. A `REQUIRED_FIELD` rule naming a field
outside its document type's list is rejected by the API, not silently
ignored.

## Status and evidence

**`OverallStatus`** — `READY` (제출 가능 — ADVS found no issue, not an
official approval), `REVIEW_REQUIRED` (확인 필요 — a human needs to look),
`NEEDS_CORRECTION` (보완 필요 — a rule failed). Precedence:
`NEEDS_CORRECTION > REVIEW_REQUIRED > READY`, computed the same way at both
the per-document (`ValidationEngine`) and per-project
(`SubmissionVerificationEngine`) levels.

**`Severity`** — `INFO`, `WARNING`, `ERROR`, attached to one
`ValidationIssue`. A missing required field is always `WARNING` regardless
of a configured rule's stated severity — a deliberate, tested invariant
(see "missing evidence is never a deterministic failure" below).

**`RuleType`** — the 12 kinds of check `ValidationEngine` can run:
`REQUIRED_DOCUMENT`, `REQUIRED_FIELD`, `DATE_NOT_EXPIRED`,
`ISSUE_DATE_MAX_AGE`, `APPLICANT_NAME_MATCH`, `COMPANY_NAME_MATCH`,
`BUSINESS_REGISTRATION_NUMBER_MATCH`, `DUPLICATE_DOCUMENT`,
`EXPECTED_DOCUMENT_TYPE`, `CUSTOM_TEXT_RULE`, `FIELD_COMPARISON`,
`DATE_COMPARISON`, `NUMERIC_COMPARISON`.

**`EvidenceSufficiencyPolicy`** — the trust gate a rule must pass through
before it may consume a machine-extracted field. Classifies each field as
`SUFFICIENT`, `REVIEW_REQUIRED`, or `UNAVAILABLE`. Confidence is not treated
as a correctness probability; page-average or classification confidence
never substitutes for a field's own evidence.

**Effective value** — the value a rule actually sees for a field: a current
human correction, else a confirmed machine value, else a sufficiently
evidenced machine value, else unavailable — in that priority order.

**Evidence / `EvidenceRef`** — the provider-independent record of *where* a
value came from: 1-based `page_number`, the actual supporting OCR/embedded
line (`source_text`, not cleaned display text), a `bounding_box`
(top-left origin, `coordinate_space` = `pixel` for OCR or `pdf_point` for
embedded PDF text), and the line's own confidence (null for direct PDF
text — never invented as `1.0`).

**"Missing evidence is never a deterministic failure"** — the project's
core safety invariant: a field ADVS could not confidently read must never,
by itself, force `NEEDS_CORRECTION`. Pinned by
`test_missing_or_uncertain_value_never_becomes_deterministic_failure`
(`apps/api/tests/test_astra_document_state.py`).

**Look-alike document** — a real, out-of-scope document type whose title
or layout resembles a modeled type closely enough that the classifier could
confidently (and wrongly) name it as that modeled type instead of
`UNKNOWN`. E.g. 지방세납세증명서 resembling
`NATIONAL_TAX_PAYMENT_CERTIFICATE`. Tracked as audit finding F-003; a guard
exists on the unmerged `phase-b/safety-fixes` branch, not yet on `main`.

**Dormant code** — code that exists, is tested, and is reachable only by a
test importing it directly — never imported by any pipeline stage. See
`docs/ARCHITECTURE.md` §10 for the current two instances
(`document_intelligence/layout/`, `extraction/structural.py`).

## Evaluation and process terms

**Gold label (synthetic)** — a hand-authored-correct JSON label (schema
v1.1) for a generated or recreated sample under `evaluation/gold/`, scored
by `make eval-*`. Not the same system as the next item.

**Gold version (real-document round 2)** — a *separate* versioned ground
truth for the 7-document real corpus (`REAL-001..007`), independent of the
synthetic schema version: v1 → v2 (frozen for this project's P2.1
adjudication) → v3 (this session's adjudication of 3 disputed fields,
denominator 33→35). Lives under the gitignored
`evaluation/backend_round2/work/` and `evaluation/private_runtime/`. See
`evaluation/README.md`.

**Safe ID** — a non-identifying label used in every tracked file in place
of a real value: `REAL-00x` (real corpus, public numbering),
`R2-0x` (same documents, internal gold-file numbering, mapped via
`SAMPLE_TO_GOLD_KEY`), `DS-0xx` (P0-era dataset ids). Real names, numbers,
and dates never appear in a tracked file — only in gitignored
`work/`/`private_runtime/` paths.

**Phase** — one numbered or named investigation/implementation effort in
this capstone project's history, each with its own directory under
`evaluation/` (P0, P1, P2.1, P2.2, Phase A, Phase B, …) — see
`evaluation/README.md`'s "Phase history" table for the full map. Phase A
and Phase B are this session's work; Phase B is on an unmerged branch.

**F-00x finding** — one numbered item in
`evaluation/system_audit/ADVS_system_audit_report.md`, this session's
independent full-system audit, with a severity (S0 most severe, S3 least,
or "Positive"/"Informational"/"Unverified"). Cross-referenced from
`docs/ARCHITECTURE.md` §11 and `docs/RECOMMENDATIONS.md`.

**Mode A / Mode B (evaluation)** — Mode A scores the deterministic
pipeline against gold OCR text directly (no OCR provider involved). Mode B
sends the real rendered file through PaddleOCR first. See
`evaluation/README.md`.
