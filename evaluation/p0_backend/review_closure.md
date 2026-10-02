# Review closure validation (F-16)

The F-16 finding was that extracted fields sat outside the review gate: the
system extracted them, could not review them, and therefore had no human path to
resolve them. This phase enumerates every supported document type and checks the
closure property directly.

## Closure property

> Every field an extractor can produce is reviewable. No extracted field is
> structurally unreachable by a human.

| Document type | Extractor-supported | Reviewable | Unreviewable |
|---|---|---|---|
| GRADUATION_CERTIFICATE | 6 | 6 | **0** |
| CAREER_CERTIFICATE | 6 | 6 | **0** |
| BUSINESS_REGISTRATION_CERTIFICATE | 7 | 7 | **0** |
| SME_CONFIRMATION_CERTIFICATE | 6 | 6 | **0** |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | 4 | 4 | **0** |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | 4 | 4 | **0** |
| ENROLLMENT_CERTIFICATE | 5 | 5 | **0** |
| TRANSCRIPT | 6 | 6 | **0** |

**Total unreviewable extracted fields across all supported types: 0.**

The fields named in the original finding are all now reviewable:
`business_address`, `business_type`, `representative_name`,
`certificate_number` and `issue_date`.

## Optional fields stayed optional

A field becoming reviewable must not make it required. Checked per type:

| Document type | Required | Supported but optional |
|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | 2 | business_address, business_item, business_type, issue_date, representative_name |
| SME_CONFIRMATION_CERTIFICATE | 4 | certificate_number, issue_date, representative_name |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | 3 | issue_date |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | 3 | issue_date |
| GRADUATION_CERTIFICATE | 6 | none |
| CAREER_CERTIFICATE | 6 | none |
| ENROLLMENT_CERTIFICATE | 5 | none |
| TRANSCRIPT | 6 | none |

No optional field was promoted to required anywhere. Specifically,
`business_address` and `certificate_number` are reviewable without being
required, and `issue_date` is optional for the business family.

`issue_date` is **required** for the student and career family
(enrollment, transcript, graduation, career) and **optional** for the business
family. That is the pre-existing domain design and it was left unchanged.

## Workflow-critical unresolved fields have a human path

Confirmed on live documents, not only in the schema:

- every document that ended `REVIEW_REQUIRED` offered review items for its
  unresolved required fields, 3 to 4 per document
- every offered item had queue status `PENDING`
- the four review decisions were all accepted and behaved as specified

| Decision | HTTP | Effect |
|---|---|---|
| `CONFIRMED` | 201 | original value becomes effective, source `HUMAN_CONFIRMED`, assessment `SUFFICIENT` |
| `CORRECTED` with a valid value | 201 | corrected value effective, source `HUMAN_CORRECTED`, assessment `SUFFICIENT`, `processing_version` advanced |
| `CORRECTED` with an invalid value | 400 | rejected; the production normaliser refuses it |
| `CORRECTED` with no value | 422 | rejected |
| `REJECTED` | 201 | value withdrawn, source `UNAVAILABLE` |
| `CANNOT_DETERMINE` | 201 | value withdrawn, recorded as human-indeterminate |
| stale `expected_processing_version` | 409 | stale review never silently applied |

A confirmed or corrected value upgrades the field's evidence assessment to
`SUFFICIENT`, which is what allows a deterministic rule to consume it. A
reviewer can therefore genuinely clear an `OCR_UNCERTAIN` gate rather than only
annotating it.

## Review durability

Reprocessing a reviewed document supersedes the human review with the new machine
result and increments `processing_version`, so a stale review can never be
silently reused against a newer extraction. Review history is retained and
readable with `include_history=true`.

## Consequence worth stating plainly

Closure is complete, but on scanned input the review queue is the *only* route to
`READY`: every OCR-sourced value requires human confirmation first. All seven
corpus documents ended in `REVIEW_REQUIRED` for exactly this reason. The closure
property is satisfied; the residual cost is review effort, not dead ends.