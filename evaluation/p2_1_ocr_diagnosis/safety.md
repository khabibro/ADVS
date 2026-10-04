# Safety

The primary safety property is not accuracy. It is that the system never
asserts something it cannot support. Every check below is a claim the system
must **refuse** to make.

## Headline

| Property | Result |
|---|---|
| **False READY** | **0 / 7** — no document reached READY |
| Wrong non-null values | **1** — unchanged from baseline, still review-gated |
| Null safety | held — no field invented where evidence was absent |
| UNKNOWN handling | correct |

## End-to-end workflow, real OCR, all seven documents

Every document ran the full production path: create project → select workflow →
upload → process → classification → extraction → verification → review →
human correction → re-verify → reprocess.

| Safe ID | Type | Terminal | Verification | Issues raised | Review items | Fields | Non-null | Wrong non-null |
|---|---|---|---|---|---|---|---|---|
| REAL-001 | SOCIAL_INSURANCE_PAYMENT | COMPLETED | NEEDS_CORRECTION | 3 | 4 | 4 | 1 | 0 |
| REAL-002 | BUSINESS_REGISTRATION | COMPLETED | NEEDS_CORRECTION | 3 | 3 | 7 | 2 | 0 |
| REAL-003 | TRANSCRIPT | COMPLETED | NEEDS_CORRECTION | 3 | 3 | 6 | 3 | **1** |
| REAL-004 | TRANSCRIPT | COMPLETED | NEEDS_CORRECTION | 3 | 3 | 6 | 1 | 0 |
| REAL-005 | ENROLLMENT | COMPLETED | NEEDS_CORRECTION | 3 | 3 | 5 | 2 | 0 |
| REAL-006 | ENROLLMENT | COMPLETED | NEEDS_CORRECTION | 3 | 3 | 5 | 3 | 0 |
| REAL-007 | SME_CONFIRMATION | COMPLETED | NEEDS_CORRECTION | 2 | 5 | 7 | 7 | 0 |

**7/7 COMPLETED, 7/7 NEEDS_CORRECTION, 0 READY.** The issues raised are
`MISSING_REQUIRED_DOCUMENT`, `OCR_UNCERTAIN` and `REQUIRED_FIELD_UNRESOLVED` —
the system is naming its own gaps rather than papering over them.

**Honest caveat on `NEEDS_CORRECTION`:** the probe seeds a checklist that marks
every document type `required`, so `MISSING_REQUIRED_DOCUMENT` fires on all
seven by construction. `NEEDS_CORRECTION` is therefore partly an artifact of
the probe's own configuration. What that configuration cannot manufacture is
READiness — the missing-required-document rule pushes away from READY, never
toward it. The claim that stands is **0/7 READY**; the specific status is
configuration-dependent.

Every document also carried `OCR_UNCERTAIN`, so the evidence policy gated 7/7.
No field on any document was assessed sufficient.

## Idempotency and state

| Check | Result |
|---|---|
| Field values stable after reprocessing | **7/7 identical** |
| Duplicate document rows created | **0** (exactly 1 row per project) |
| Terminal status after reprocess | stable |

## The one wrong non-null value

Full trace, as required.

| Property | Value |
|---|---|
| Safe ID / field | REAL-003 / `student_name` |
| What the document shows | A three-character personal name, legible to a human |
| Was the label read correctly | **Yes** — `성명` recognised correctly |
| OCR detection | Box present, correct position |
| OCR confidence | **0.9166** |
| Character recall vs human reading | 2 / 3 — one character wrong |
| Evidence refs attached | 5 |
| Candidate generation | 1 candidate, via `spatial_right_of_label` |
| Shape-valid candidates considered | 4 |
| Candidate selected | the only candidate — no ambiguity |
| Normalisation | correct, no error introduced |
| Field resolution | **confident, non-null, wrong** |
| Extraction `needs_review` flag | **False** |
| Evidence policy | **REVIEW_REQUIRED** |
| Review item | **raised** |

### Root cause

**OCR recognition error**, and nothing else. Not candidate selection, not
association, not normalisation, not extraction.

The evidence for that attribution is specific:

- The label was recognised correctly, so the failure is not in label matching.
- Exactly one candidate existed and it was the mis-transcribed one, so
  selection had nothing to choose between.
- The character-recall measure isolates the defect to a single character in
  the recogniser's output.
- The extracted value equals the OCR output exactly, so no downstream stage
  altered it.

The **extraction layer's own `needs_review` flag was False.** The field was
still gated, but only because the evidence policy independently caught low
confidence relative to policy — 0.9166 sits near the 0.90 threshold and was
caught by the OCR-requires-confirmation rule, not by the extractor's own
judgement.

That is a real finding: **a high-confidence recognition error is not
self-flagging.** It was caught here by the evidence policy, which is the last
line of defence rather than the first. A slightly higher confidence on the
same error would have needed a human to notice.

### Does it remain safely review-gated?

**Yes.** Confirmed three independent ways:

1. Evidence assessment is `REVIEW_REQUIRED`, so it cannot be presented as
   verified.
2. A review item was raised against it.
3. Submission verification returned `NEEDS_CORRECTION`, not READY.

### Confidence is not correctness

This field is the corpus's counter-example to any assumption that OCR
confidence indicates accuracy: **confidence 0.9166 on a value that is wrong.**
Recorded so it is not forgotten, and so no future threshold is tuned on the
assumption that high confidence means high accuracy.

## Human correction keeps its own evidence source

Verified where a reviewable non-null field existed:

| Property | Observed |
|---|---|
| Machine value after human correction | **preserved unchanged** |
| Effective value | the human's value |
| `effective_source` | `HUMAN_CORRECTED` |
| Review decision recorded | `CORRECTED` |

A human correction **overrides** the effective value without **overwriting** the
machine value. The two are stored separately, so machine evidence and human
evidence remain distinguishable and the correction is auditable. This is the
required separation and it holds.

## Safety matrix

Two layers, because they answer different questions. Uploads accept only
pdf/png/jpg/jpeg/webp, so text-driven scenarios are driven through the
filename-hint fixtures over HTTP, and the "a field is missing, nothing may be
invented" rules are driven directly against the validation engine.

### End-to-end, deterministic provider

| Scenario | Expected | Observed |
|---|---|---|
| Happy path | fields resolve | 6/6 resolved; verification `NEEDS_CORRECTION`; **never READY** |
| Inferred issue date | review-gated | `REVIEW_REQUIRED` on the field; **never READY** |
| Truncated reference document | `REVIEW_REQUIRED` | 4 fields `UNAVAILABLE`, `REVIEW_REQUIRED`; **never READY** |
| Genuine expiry | needs correction | `NEEDS_CORRECTION`; **never READY** |
| **UNKNOWN document** | **UNKNOWN** | **`UNKNOWN`**, `UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW`, no fields |
| Empty OCR result | fail closed | **`FAILED`**, no fields, no value |
| OCR provider error | fail closed | **`FAILED`**, no fields, no value |
| Duplicate upload | configured result | second upload accepted; `DUPLICATE_UPLOAD` raised at engine level (see below) |

### Rule level, validation engine

| Rule under test | Expected | Observed |
|---|---|---|
| All fields present | no failures | no failures |
| **Missing business number** | **no invented value, no false mismatch** | **no mismatch raised** |
| **Missing validity date** | **no false expiry** | **no expiry raised** |
| **Missing issue date** | **no false date failure** | **no date failure raised** |
| Wrong identity | error | `COMPANY_NAME_MISMATCH` |
| Duplicate | configured, not a crash | `DUPLICATE_UPLOAD` warning |
| **Genuine expiry** | error | **`EXPIRED_DOCUMENT`** |
| Unexpired validity | silent | silent |

Every "must not invent" rule holds. Every "must catch" rule fires.

### Two limits on this matrix, stated plainly

1. **`DUPLICATE_DOCUMENT` is refused by submission verification** with
   *"not supported for submission verification; configure an explicit
   comparison rule"*. Duplicate detection therefore works at the document
   validation layer but cannot be surfaced through submission verification as
   configured. This is deliberate refusal rather than silent acceptance — the
   safe direction — but it means duplicate handling is not reachable end to
   end through the current rule set.
2. **The `genuine_expiry` end-to-end row is not attributable to the expiry
   rule.** It reached `NEEDS_CORRECTION`, but so did every other scenario,
   because `MISSING_REQUIRED_DOCUMENT` fires everywhere under this probe's
   checklist. The `EXPIRED_DOCUMENT` result in the rule-level table is the
   actual evidence that expiry is caught.

## Null safety

| Property | Result |
|---|---|
| Values invented where none was printed | **none** |
| Absent-by-design fields filled | **none** — REAL-001 `valid_until`, REAL-005 `student_id` both correctly `null` |
| Cross-page field pairing | none — rows are page-scoped, confirmed by the multipage test |
| Missing evidence became a fabricated value | **no** |

## UNKNOWN and out-of-scope

`UNKNOWN` documents produce `UNKNOWN`, raise
`UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW`, and yield no fields and no values.

**Caveat:** the frozen corpus contains **no** `NEGATIVE_OUT_OF_SCOPE`
document, so out-of-scope rejection is evidenced only by synthetic fixtures,
not by real material. Filename-based classification shortcuts remain
structurally impossible — the classifier ignores the filename by design and
logs that it did so — but this is design evidence, not a measurement on real
out-of-scope input.
