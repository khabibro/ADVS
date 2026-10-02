# Live HTTP validation

A normal local ADVS stack was started against a scratch database and scratch
storage, and driven **only** through real HTTP endpoints with `httpx`. No
service class, extractor or OCR provider was called directly. Raw
`uvicorn app.main:app` plus the standard seed script, i.e. the ordinary
deployment path.

Sequence exercised per document: upload → storage validation → processing →
OCR → classification → extraction → evidence → persistence → verification →
re-fetch.

## Result summary

All seven supported Desktop samples went through the full HTTP boundary.

| Sample | Upload | Process | Type | Persistence | Submission |
|---|---|---|---|---|---|
| DS-001 | 201 | COMPLETED | correct | stable | REVIEW_REQUIRED |
| DS-002 | 201 | COMPLETED | correct | stable | REVIEW_REQUIRED |
| DS-003 | 201 | COMPLETED | correct | stable | REVIEW_REQUIRED |
| DS-004 | 201 | COMPLETED | correct | stable | REVIEW_REQUIRED |
| DS-005 | 201 | COMPLETED | correct | stable | REVIEW_REQUIRED |
| DS-006 | 201 | COMPLETED | correct | stable | REVIEW_REQUIRED |
| DS-007 | 201 | COMPLETED | correct | stable | REVIEW_REQUIRED |

- Documents uploaded and processed over HTTP: **7 / 7**
- Upload rejections: **0**
- Processing failures: **0**
- Read-back stable after re-fetch: **7 / 7** (refresh returns exactly what was persisted)
- Submissions reaching `READY`: **0**
- `REVIEW_REQUIRED` review items offered per document: 3–4

## Submission workflows over HTTP

| Scenario | Status | Issue codes |
|---|---|---|
| Business pack, 3 of 4 documents | NEEDS_CORRECTION | `MISSING_REQUIRED_DOCUMENT`, `OCR_UNCERTAIN`, `REQUIRED_FIELD_UNRESOLVED` |
| Student pack, 2 documents | REVIEW_REQUIRED | `OCR_UNCERTAIN`, `REQUIRED_FIELD_UNRESOLVED` |
| No documents at all | NEEDS_CORRECTION | missing-document rule |
| Single document on a multi-document checklist | NEEDS_CORRECTION | `MISSING_REQUIRED_DOCUMENT` |

`MISSING_REQUIRED_DOCUMENT` on a three-document business submission is correct:
the configured checklist requires the national tax payment certificate, which is
not present in the corpus. ADVS did not treat the partial pack as acceptable.

## `UNKNOWN` handling over HTTP

A synthetic out-of-scope document (a driving-licence-style form, generated for
this test, not from the corpus) was uploaded and processed.

- Classified `UNKNOWN`
- **Zero** fields extracted, **zero** populated values
- Document status `REVIEW_REQUIRED`
- Submission `REVIEW_REQUIRED` with `UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW`

No invented fields, no forced known class, no `READY`.

## Review lifecycle over HTTP

On a real unresolved field of a real document:

| Action | Result |
|---|---|
| `CONFIRMED` | 201 |
| `CORRECTED` with a valid value | 201, `effective_normalized_value` set, `effective_source` = `HUMAN_CORRECTED`, assessment upgraded to `SUFFICIENT` |
| `CORRECTED` with an invalid value | 400 — rejected, not silently stored |
| `REJECTED` | 201 |
| `CANNOT_DETERMINE` | 201 |
| Stale `expected_processing_version` | 409 `STALE_PROCESSING_VERSION` |
| `CORRECTED` with no value | 422 |

A human-corrected value becomes effective and is marked `HUMAN_CORRECTED`, so a
reviewer can legitimately move a field from gated to usable. After
reprocessing, the machine result supersedes the human review and review history
is retained.

## Concurrency over HTTP

Three distinct documents submitted and processed simultaneously against the live
server.

| Document | Upload | Result | Error | Duration |
|---|---|---|---|---|
| 1 | 201 | COMPLETED | none | 12.6 s |
| 2 | 201 | COMPLETED | none | 25.5 s |
| 3 | 201 | COMPLETED | none | 19.2 s |

Wall clock 25.9 s against a summed 57.3 s of serial work, confirming the
requests genuinely overlapped. All three were accepted, all three eventually
processed, and **no request returned `OCR_BUSY`**. The second and third requests
waited for the single OCR slot rather than failing. See `concurrency_validation.md`.

Same-document concurrent `POST /process` calls: all four returned 200, none
carried an error code, the document converged to `COMPLETED`, the extracted
field set was byte-identical before and after, and `processing_version` advanced
monotonically. The callers that observed an in-flight status were refused the
claim by the atomic status transition and returned the current state unchanged,
which is the intended idempotency behaviour, not a failure.

## Storage security over HTTP

A filename containing `../` traversal segments was accepted, and:

- exactly one file was created
- the stored name contains no path separators and no `..`
- nothing was written outside the storage root
- the stored bytes are exactly the uploaded bytes
- the document still classified correctly from its bytes

Storage trusts the bytes on disk over the client-declared extension and content
type, so a PDF sent with a PNG content type is stored and processed as the PDF it
actually is. This is deliberate and is not a finding.

## Notes on interpretation

Three initial failures in this phase were traced to defects in the validation
script, not in ADVS, and were corrected before conclusions were drawn:

1. reading the submission status from a field name the schema does not use;
2. asserting a wrong response key for the human-correction source;
3. asserting a document's classification before processing it had been
   requested.

Each was re-tested and passed. They are listed here so the record shows they were
investigated rather than assumed benign.