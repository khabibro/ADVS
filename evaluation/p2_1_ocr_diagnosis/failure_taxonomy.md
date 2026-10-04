# Failure Taxonomy

## Categories used

Exactly one primary diagnosis per field, first matching rule wins. The order
is deliberate: it walks the pipeline from the pixels forward, so the category
names the **earliest** stage that failed, which is the stage a fix must act on.

| Category | Definition used here |
|---|---|
| `DETECTION_FAILURE` | A human read the value; its characters are not recoverable from any observation on the page. |
| `RECOGNITION_FAILURE` | Glyphs were detected but the recognised characters do not convey the value — including the case where a **label** was misread and so the alias match could not fire. |
| `EXTRACTION_FAILURE` | OCR conveyed the value correctly; the backend produced no field, or the field's alias set does not contain the label the document prints. |
| `STRUCTURAL_INTERPRETATION_FAILURE` | The information is present and readable, but choosing it among competing readings, or resolving it at all, requires the document's row/section/block structure. |
| `ASSOCIATION_FAILURE` | OCR read the value correctly *at its position* and a different value was produced. |
| `SOURCE_ABSENT` | The document does not carry the value. Absence is the truth. |
| `SOURCE_UNREADABLE` | A human cannot read the value at the document's own resolution. |
| `AMBIGUOUS` | The evidence does not separate the categories. |
| `NOT_EVALUATED` | The frozen scorer does not evaluate this field for this document. |

## Decision order

Evaluated, in order. First match wins.

1. Not evaluated (absent from gold, or gold category `AMBIGUOUS`/`NOT_EVIDENCED`)
2. `SOURCE_ABSENT` — value absent by design, or `VERIFIED_ABSENT`
3. `SOURCE_ABSENT` — no value visible
4. `SOURCE_UNREADABLE` — not readable by a human
5. `DETECTION_FAILURE` — characters not recoverable page-wide
6. `NONE` — OCR correct **and** extraction correct
7. OCR conveyed the value but nothing was produced:
   7a. `DETECTION_FAILURE` — no observation covers the printed label
   7b. `EXTRACTION_FAILURE` — the printed label is not in the field's alias set
   7c. `RECOGNITION_FAILURE` — the printed label is not recoverable from OCR text
   7d. `STRUCTURAL_INTERPRETATION_FAILURE` — more than one competing candidate value
   7e. `EXTRACTION_FAILURE` — bare date refused by the issuance-block inference
   7f. `STRUCTURAL_INTERPRETATION_FAILURE` — no label printed for this field
   7g. `EXTRACTION_FAILURE` — no other explanation
8. OCR conveyed the value, wrong value produced: `AMBIGUOUS` if it happened to
   be right, else `ASSOCIATION_FAILURE`
9. OCR did not convey the value: `RECOGNITION_FAILURE` whether or not a value
   was produced

Step 7b sits **before** 7c on purpose. A label that is missing from the alias
set is an extraction defect no matter what OCR did with it, and it is the
actionable one. Step 9 folds "OCR was wrong" together because recognition
errors propagate: a wrong label and a wrong value are the same defect at
different fields, and splitting them would over-count.

## Two booleans that must not be collapsed

`label_in_alias_set` and `label_recovered` are recorded separately for every
field, because they are independent facts with different fixes:

| | label recovered from OCR | Label in alias set | Meaning | Fix belongs to |
|---|---|---|---|---|
| 1 | yes | yes | healthy | — |
| 2 | yes | **no** | extractor vocabulary gap | extraction |
| 3 | **no** | yes | recognizer read the label wrong | recognition |
| 4 | **no** | **no** | both | both, extraction first |

Collapsing these to "label failed" hides whichever one is actionable. On this
corpus REAL-006 `department` is case 4, and its extraction defect alone is
sufficient to explain the failure.

## CONFIRMED vs NOT CONFIRMED

This distinction is the point of the phase, so it is stated explicitly.

**Confirmed by measurement:**

- 0 detection failures, out of 33 evaluated fields, using a page-wide test.
- 6 recognition failures, each traced to a specific mis-transcribed string.
- 4 extraction-path failures, each traced to a specific rule or alias gap.
- 5 structural failures, 4 of which have more than one competing candidate
  value recorded.

**NOT confirmed — the evidence does not support a claim either way:**

- **True detection recall.** No claim is made. 26 of 28 checkable values were
  observed at their own position, but the annotation regions were refined
  against the observation stream, so region-level recall is partly circular.
  The page-wide test removes the circularity for presence but says nothing
  about **fragmentation** — whether one text line was split into several boxes
  or two adjacent lines merged into one. Nothing in this phase measures
  either. No box-count or merge/split metric was computed.
- **That 0 detection failures means none exist.** Two fields could not be
  tested at all (no gold value). If a value were missing from a document in a
  way the frozen gold describes as present-but-unreadable, this phase would
  not have found it.
- **Per-document OCR quality.** With 1–5 evaluated fields per document, no
  document-level rate is meaningful. Only the pooled 33-field distribution is
  reported.
- **Whether the misread labels are a threshold, model, or resolution
  problem.** Three label errors are single-character substitutions on short,
  letter-spaced, low-contrast text. Those have several plausible causes and
  this phase did not separate them.
- **Recall and precision as normally defined.** Not computed. Observation-level
  gold supports the categorical per-stage judgements above and nothing more.

## Reproducibility notes

- Thresholds used: region coverage 0.25, character recall 0.6. Both are
  constants in `build_observation_matrix.py` and are printed with every run.
- Comparison is format-insensitive (hyphens, en dashes, date particles and
  letter-spacing are removed before comparison). An earlier run that compared
  raw strings mis-classified correct readings as recognition errors; the
  format-insensitive key is what fixed that, and the matrix has been stable
  across three consecutive runs since.
- The evaluated-field denominator is 33, identical to the frozen scorer, so
  the diagnosis distribution and the historical score are directly comparable.
