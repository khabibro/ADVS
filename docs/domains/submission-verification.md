# Submission verification

`SubmissionVerificationService` is the authoritative project-level verification path. It loads
the selected `Checklist`, its `DocumentRequirement` and `ValidationRule` rows, and persisted
`Document`/`ExtractedField` state. It never opens document files, reruns OCR, searches OCR text,
or changes extracted values.

```text
Project
  -> Checklist requirements and configured rules
  -> persisted canonical document fields
  -> SubmissionVerificationEngine
  -> RuleEvaluationResult[]
  -> VerificationIssue[]
  -> READY / REVIEW_REQUIRED / NEEDS_CORRECTION
```

## Rule configuration

Requirements retain required/optional document semantics. `ValidationRule.params` stores the
small deterministic rule configuration needed by the current workflows:

- `FIELD_COMPARISON`: `EQUALS` over existing normalized string or identifier fields.
- `DATE_COMPARISON`: `ON_OR_BEFORE` or `ON_OR_AFTER`, against either a configured ISO date or
  the request's explicit `evaluation_date`.
- `NUMERIC_COMPARISON`: `GREATER_THAN_OR_EQUAL`, `LESS_THAN_OR_EQUAL`, or `EQUALS`, using
  `Decimal` rather than binary floating point.

Unknown document types or fields, malformed dates/decimals, and incompatible operators reject
verification as invalid configuration. Rule parameters are data, never executable expressions.

## Outcomes and null semantics

Every rule has one of four outcomes:

- `PASS`: the available structured values satisfy the condition.
- `FAIL`: both sides are available and the configured condition is clearly false.
- `UNRESOLVED`: an applicable document exists, but a required field is absent or marked for
  review.
- `NOT_APPLICABLE`: an optional document is absent, or a dependent rule cannot run because a
  required document is already represented by its own missing/processing issue.

Unknown is not failure. In particular, a missing `valid_until` is not expired, a missing GPA is
not below threshold, and a missing business number is not a mismatch. These cases produce
`REQUIRED_FIELD_UNRESOLVED` and `REVIEW_REQUIRED`.

## Reference documents and comparison

The business workflow's comparison rules explicitly name
`BUSINESS_REGISTRATION_CERTIFICATE` as their source type. The engine does not select a reference
by row order. Missing reference documents generate one `MISSING_REQUIRED_DOCUMENT` issue;
dependent comparisons become `NOT_APPLICABLE` without mismatch cascades. Multiple distinct
completed documents of one configured type produce `MULTIPLE_DOCUMENTS_REQUIRE_REVIEW`; exact
checksum duplicates collapse deterministically.

Comparisons use persisted normalized values exactly. Company and workplace fields remain
semantically distinct and are compared only when a workflow rule explicitly pairs them. No
fuzzy or legal-designator equivalence is applied.

## Dates, status, and READY

The caller supplies one explicit evaluation date to `POST /projects/{project_id}/verify`.
Validity is inclusive: `valid_until == evaluation_date` passes. Fixed student issue-date and GPA
thresholds are seeded demo/workflow criteria, not universal policy.

Status precedence is deterministic:

```text
NEEDS_CORRECTION > REVIEW_REQUIRED > READY
```

Clear configured failures create correction issues; unresolved evidence creates review issues.
Both remain visible when they coexist. `READY` means only: “현재 설정된 점검 기준에서 확인된
문제가 없습니다.” It is not official acceptance or legal approval.

## Persistence and staleness

Submission rule results reuse `ValidationResult` with `scope=SUBMISSION`, a four-state `outcome`,
and structured reference metadata. Re-verification transactionally replaces the previous result
set, so issues do not accumulate. Uploading a document, changing the project's workflow inputs,
or starting document reprocessing deletes the prior submission result and resets the project to
`REVIEW_REQUIRED`. `GET /projects/{project_id}/verification` then returns `is_current=false`
until explicit re-verification.

The MVP keeps only the latest result and uses database transactions without distributed locks.
Concurrent verifications are last-commit-wins; production-grade history and distributed
coordination remain deferred.
