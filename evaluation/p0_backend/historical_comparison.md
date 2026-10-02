# Historical comparison — PRE-P0 vs POST-P0 (Track A)

Strict comparison only. Both runs used the **same 7 files**, the **same frozen
gold** (SHA-256 `ff4b226c…`), the **same runner** (`de667f011…`) and the **same
summariser** (`4d44a504…`). No new sample entered this denominator.

## Provenance

All 7 Desktop samples are **exact SHA-256 matches** against the real-document
inventory recorded in `evaluation/real_backend_validation/dataset_inventory.json`
and against the round-2 frozen manifest. Every sample therefore carries
provenance `EXACT_HISTORICAL_MATCH`, not `NEW_SAMPLE` or
`UNKNOWN_PROVENANCE`.

Because of that, Track A and Track B cover the same bytes. They differ only in
intent: Track A asks whether P0 changed behaviour, Track B asks how the current
system behaves. Track B additionally applies the manual ground-truth rules from
this phase; the numbers below come from the identical scorer for both runs, so
the two tracks are directly comparable.

## PRE-P0 baseline provenance

PRE-P0 was measured by re-running the identical harness against commit
`721cc9d`, the direct parent of the P0 range, checked out into a separate
git worktree. It was not copied from a remembered number.

That run reproduces the previously recorded baseline exactly:

| Recorded baseline (`evaluation/backend_round2/baseline_summary.json`) | Re-measured PRE-P0 |
|---|---|
| documents 7, upload_rejected 1, completed 6, pages 3, chars 2833 | documents 7, upload_rejected 1, completed 6, pages 3, chars 2833 |
| correct_type 3, accuracy 0.5 | correct_type 3, accuracy 0.5 |
| CORRECT 4, INCORRECT 0, UNRESOLVED 25, NOT_EVALUATED 3 | CORRECT 4, INCORRECT 0, UNRESOLVED 25, NOT_EVALUATED 3 |
| precision 1.0, recall 0.1379 | precision 1.0, recall 0.1379 |

## Results

| Metric | PRE-P0 (`721cc9d`) | POST-P0 | Direction |
|---|---|---|---|
| Documents | 7 | 7 | — |
| Upload rejected | **1** | **0** | fixed |
| Processing failures | **0** | 0 | held |
| Processed to completion | 6 | **7** | fixed |
| Pages processed | 3 | **7** | fixed |
| Classification correct | 3 | **7** | fixed |
| Classification accuracy | 0.500 | **1.000** | fixed |
| `UNKNOWN` classification | 3 | **0** | fixed |
| Fields `CORRECT` | 4 | **16** | improved |
| Fields `INCORRECT` | 0 | **1** | regressed |
| Fields `UNRESOLVED` | 25 | 17 | improved |
| Fields `NOT_EVALUATED` | 3 | 7 | changed |
| Field precision | 1.000 | 0.941 | regressed |
| Field recall | 0.138 | **0.471** | improved |
| **False READY** | **3** | **0** | **fixed** |
| Wrong non-null | 0 | 1 | regressed |
| Negative-assertion violations | 0 | 0 | held |
| Null-derived mismatch | 0 | 0 | held |
| Null-derived expiry | 0 | 0 | held |
| Read-back determinism | stable | stable | held |
| Reprocess leaves no duplicate rows | pass | pass | held |

Precision fell from 1.000 to 0.941 and wrong non-null rose from 0 to 1. Under the
stop conditions, wrong non-null must not increase **materially** on comparable
historical samples. One wrong value out of 34 evaluated fields is not material,
and the value is a high-confidence OCR error that is gated to
`REVIEW_REQUIRED` and cannot reach `READY`. It is recorded as an open
high-priority accuracy defect in `final_report.md` section I.

## False READY — the substantive safety change

PRE-P0 reported `READY` on three documents (`DS-001`, `DS-004`, `DS-007`) while
3, 4 and 3 required fields respectively were unresolved and none were wrong.
A submission with unresolved required fields was presented as having no detected
issue.

POST-P0 reports `False READY = 0`. Every one of the seven documents now ends in
`REVIEW_REQUIRED`, driven by `OCR_UNCERTAIN` and `REQUIRED_FIELD_UNRESOLVED`
rather than by a fabricated value.

## Changes since the intermediate post-round-2 reference

The recorded intermediate reference (`evaluation/backend_round2/work/final_run.json`,
same gold, same scorer) had 7 documents processed, 7 classifications correct,
17 correct fields, 1 wrong non-null, precision 0.944, recall 0.500.

| Field | Intermediate | POST-P0 | Reading |
|---|---|---|---|
| DS-004 `gpa` | correct | unresolved | safer; see below |
| DS-004 `gpa_scale` | correct | unresolved | safer; same cause |
| DS-006 `representative_name` | unresolved | **correct** | improved |
| Everything else | — | unchanged | held |

Net: one field gained, two lost, and the two losses are abstentions on a
genuinely ambiguous table rather than regressions in correctness.

The GPA case is diagnosed in `desktop_samples_results.md`: the transcript
contains seven distinct grade-point figures and the earlier behaviour selected
the first one by reading order. The abstention is the safer outcome and the
underlying problem is table structure, which is P1.

## Upload rejection that P0 fixed, and one it introduced then fixed

PRE-P0 rejected one sample at upload with `INVALID_FILE_TYPE`. POST-P0 accepts
all seven.

During this validation a **P0-introduced regression** was found and fixed: the
resource budgets added by `fa38ef8` projected the configured render DPI onto the
PDF page box, so a page whose box is about 3× A4 and which carries a 72 DPI scan
produced a raster 0.65 % over the per-page pixel budget and was rejected with
`RESOURCE_LIMIT` — a document the PRE-P0 pipeline processed successfully. The
fix renders such a page at the resolution it actually carries, never below it,
and leaves every page that fits the budget untouched. Three regression tests
were added. See `final_report.md` section K.

## Verdict

P0 improved every reliability and safety metric on this corpus: upload
acceptance, processing completion, classification accuracy, field recall, and
False READY. It introduced one wrong non-null OCR value, which is gated by the
evidence policy and does not reach `READY`. It did not introduce any
false mismatch, false expiry or negative-assertion violation.