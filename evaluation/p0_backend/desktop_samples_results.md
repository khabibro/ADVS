# Desktop sample evaluation — current backend (POST-P0)

Track B. This is the current ADVS measured on the owner's Desktop sample corpus.
No names, identifiers, addresses, business numbers or raw OCR text appear here.

## Corpus composition

| Metric | Value |
|---|---|
| Folder located | yes — a `samples` folder directly under the owner's Desktop |
| Files | 7 |
| Unique SHA-256 | 7 (no duplicates) |
| PDFs | 3 |
| Images | 4 (`.png`, `.jpeg` ×2, `.webp`) |
| Single-page | 7 |
| Multi-page | 0 |
| Born-digital | 0 |
| Scanned / image-only | 7 |
| Embedded PDF text | 0 characters on all three PDFs |
| Supported document types | 7 of 7 |
| Out-of-scope samples | 0 |
| Unsafe or corrupt | 0 |
| Absolute Desktop path recorded | no (deliberately omitted) |

Every sample is an image-only scan. No sample exercises the embedded-PDF-text
route, so the "digital PDF" ingestion path is **not** exercised by this corpus.

Per-sample detail, with no filenames, is in `desktop_samples_inventory.json`.

## Frozen denominator

Recorded before any model output was inspected and unchanged afterwards.

| Item | Value |
|---|---|
| Files | 7 |
| Sample ids | `DS-001` … `DS-007` |
| Ground-truth SHA-256 | `ff4b226c946b78d79ee320c3e30fd349ca715a7db18c403159088e9b05e53893` |
| Runner SHA-256 | `de667f011d196c8cdbc292bd2a198a82d7b752c899957492fb165b9a15db8f64` |
| Summariser SHA-256 | `4d44a504c89eab8a636f5067879164473f7ac0daf2f1e3b9b6155d13aaa1a8fc` |
| Evaluable fields | 34 |
| Verdict vocabulary | `CORRECT` / `INCORRECT` / `UNRESOLVED` / `NOT_EVALUATED` |

`None == None` is never scored as a successful extraction: a `VERIFIED_ABSENT`
field scores `CORRECT` only when the machine also produced nothing.

The runner hash is for `run_round2.py` **after** a path-resolution fix
described under *Harness blocker* below.

## Harness blocker and why it was fixed rather than accepted

The earlier P0 attempt was recorded `BLOCKED` because the runner raised
`FileNotFoundError` for every sample. The cause was **not** a missing fixture:
the files exist. The runner searched the Desktop root, while the samples live in
a `samples` subfolder.

Resolution: the runner now searches the sample subfolders and then the Desktop
root, read-only, with an `ADVS_SAMPLE_DIR` override. No source file was moved,
renamed, copied or modified. Gold, denominator and verdict semantics are
untouched, so the comparison in `historical_comparison.md` stays valid.

## Classification

| Sample | Expected | Predicted | Result |
|---|---|---|---|
| DS-001 | SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | correct |
| DS-002 | BUSINESS_REGISTRATION_CERTIFICATE | BUSINESS_REGISTRATION_CERTIFICATE | correct |
| DS-003 | TRANSCRIPT | TRANSCRIPT | correct |
| DS-004 | TRANSCRIPT | TRANSCRIPT | correct |
| DS-005 | ENROLLMENT_CERTIFICATE | ENROLLMENT_CERTIFICATE | correct |
| DS-006 | SME_CONFIRMATION_CERTIFICATE | SME_CONFIRMATION_CERTIFICATE | correct |
| DS-007 | ENROLLMENT_CERTIFICATE | ENROLLMENT_CERTIFICATE | correct |

Correct **7 / 7**, incorrect **0**, `UNKNOWN` **0**, processing failures **0**.
Every document in this corpus is now correctly classified; at the PRE-P0
reference only 3 of 7 were correct and 3 were `UNKNOWN`.

## Field extraction

| Verdict | Count |
|---|---|
| `CORRECT` | 16 |
| `INCORRECT` (wrong non-null) | 1 |
| `UNRESOLVED` | 17 |
| `VERIFIED_ABSENT` scored `CORRECT` | included in the 16 |
| `NOT_EVALUATED` | 7 |
| Hallucinated extra fields | **0** |

Field precision **0.941**, field recall **0.471** over 34 evaluated fields.

Machine-only fields were also examined. Every field the pipeline emitted is in
the extractor's supported set for its classified document type, so no field was
produced that the schema does not define. There is no
`HALLUCINATED_EXTRA_FIELD` case in this corpus.

Fields annotated `VERIFIED_ABSENT` behaved correctly: where the document prints
a placeholder dash, the pipeline produced nothing rather than inventing a value.
Both such fields scored as abstentions, not as extractions.

## Safety

| Metric | Value |
|---|---|
| **False READY** | **0** |
| Documents reaching `READY` | 0 of 7 |
| Null-derived mismatch | 0 |
| Null-derived expiry | 0 |
| Negative-assertion violations | 0 |
| Wrong non-null values | 1 |
| OCR characters persisted | 6326 across 7 pages |
| Mean per-document processing | 19.1 s (CPU PaddleOCR, one OCR slot) |

The three negative assertions carried in the gold — values the pipeline must
never produce, including a different 10-digit identifier printed under its own
label in the same table — were all respected.

The one wrong non-null value is analysed in `final_report.md` section I. It is
an OCR-derived personal-name error carried at high recognition confidence, and it
is still gated: its evidence assessment is `REVIEW_REQUIRED`, so it is nulled
before any deterministic rule consumes it, and its submission cannot reach
`READY`.

## Review burden

Every document ends in `REVIEW_REQUIRED`. Review-queue depth ranged from 3 to 4
fields per document.

This is the designed consequence of the evidence policy: any value whose
evidence comes from OCR requires independent human confirmation before a
deterministic rule may consume it. On a corpus of scanned documents, that means
**no scanned document can reach `READY` on machine output alone**. This is
conservative and correct, but it means the practical review load is high and
`READY` is currently unreachable for this corpus.

## Root-cause distribution of the 17 unresolved fields

| Root cause | Fields | Notes |
|---|---|---|
| TABLE_STRUCTURE / LAYOUT_LOSS | 6 | GPA and GPA scale in the course-table transcript; university/department where the label sits in a header band rather than beside its value |
| ROW_GROUPING | 4 | label and value in separate table cells with a large horizontal gap |
| CANDIDATE_SELECTION | 4 | several distinct candidate values for one label; the pipeline abstains rather than picking |
| CONFIDENCE_POLICY | 2 | value present but below the evidence threshold |
| OCR_RECOGNITION | 1 | field not legible in the scan |

The single most important structural finding is the GPA case, described next.

## The one wrong non-null value, and the one field that changed category

**Wrong non-null (`DS-003`, `student_name`).** OCR read a personal name at
0.917 confidence and it does not match the document. The evidence is truthful —
five OCR observations on page 1 — so provenance is honest while the value is
wrong. This is the exact case the report is meant to surface: a high OCR
confidence is not a correctness signal. It is contained by the evidence policy,
not by the confidence number.

**GPA regression against the intermediate reference (`DS-004`, `gpa`,
`gpa_scale`).** Against the pre-P0 reference these fields were correct; against
the intermediate post-round-2 reference they are now unresolved. Root cause,
established by inspecting the real OCR lines: the transcript contains **seven
distinct grade-point figures**, one per course block, each printed as
`평점평균:x/4.5`. The old behaviour took the **first regex match anywhere in the
document**, which happened to be the value the gold records as the overall
figure. The new behaviour sees seven conflicting candidates and abstains.

The old `CORRECT` verdict was therefore **right by accident** — it depended on
reading order, not on evidence, and it would have produced a confidently wrong
overall GPA on any transcript whose first block is not the overall one. The gold
annotation for this sample notes that the overall figure "is the first", which
is a convention a reader cannot verify from the page. This is recorded as a
**safer** outcome at a cost in recall, and as a **P1 table-structure problem**,
not a P0 defect.

## Accuracy rules applied

Per the accuracy rule for this phase: safe abstention, low recall and layout or
table failures are acceptable at P0 provided there are no new confident wrong
values, no False READY, no false blocking decisions, no processing corruption
and no concurrency failure. On this corpus the current backend shows one
OCR-derived wrong value that is gated by policy, zero False READY, zero
fabricated fields, zero processing failures, and correct abstention on the
ambiguous table case.

These results do **not** establish broad real-world accuracy. They establish
behaviour on seven specific scanned documents.

## What this corpus does not cover

- No multi-page document, so multi-page behaviour is validated separately with
  mechanical fixtures (`multipage_validation.md`).
- No born-digital PDF, so the embedded-text ingestion route is unexercised.
- No out-of-scope document, so the `UNKNOWN` route is validated separately with
  a synthetic document.
- No complete business pack; see `final_report.md` section V.
- No career, graduation or national-tax-payment sample, so three supported
  document types are unexercised by real input.