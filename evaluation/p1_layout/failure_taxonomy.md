# Structural failure taxonomy

Per-field root cause, established by replaying the frozen observations through
the exact production code path. No architecture was chosen before this existed.

## Method

For each field the pipeline attempted, the diagnosis follows the same path the
field helper actually takes. This matters: several helpers use the *unranked*
label path while others use the ranked, shape-gated path, and diagnosing one
through the other measures a path production never takes.

The reported category is the **first** stage that lost the value.

## Categories

| Category | Meaning |
|---|---|
| `OCR_RECOGNITION` | the label text is absent or mangled in the OCR output |
| `LABEL_DETECTION` | label text present in the page but no usable occurrence |
| `LABEL_VALUE_ASSOCIATION` | label found, no value position beside it |
| `COLUMN_STRUCTURE` | value contaminated by the adjacent column in the same box |
| `CANDIDATE_SELECTION` | candidates generated but all rejected downstream |
| `REPEATED_LABEL_AMBIGUITY` | one label, several distinct values |
| `NORMALIZATION` | candidate produced, normaliser refused it |
| `NONE` | resolved by the current model |

## Per-field findings

| Sample | Type | Field | Diagnosis | Category |
|---|---|---|---|---|
| P1-001 | social insurance | business_registration_number | no label observed | `OCR_RECOGNITION` |
| P1-001 | social insurance | valid_until | no label observed | `OCR_RECOGNITION` |
| P1-001 | social insurance | issue_date | contaminated by adjacent column | `COLUMN_STRUCTURE` |
| P1-002 | business reg. | company_name | no label observed | `OCR_RECOGNITION` |
| P1-002 | business reg. | representative_name | no label observed | `OCR_RECOGNITION` |
| P1-002 | business reg. | issue_date | no label observed | `OCR_RECOGNITION` |
| P1-002 | business reg. | business_type | no label observed | `OCR_RECOGNITION` |
| P1-002 | business reg. | business_item | label found, no value | `LABEL_VALUE_ASSOCIATION` |
| P1-003 | transcript | issue_date | no label observed | `OCR_RECOGNITION` |
| P1-003 | transcript | gpa | candidates rejected by shape | `REPEATED_LABEL_AMBIGUITY` |
| P1-003 | transcript | gpa_scale | normaliser refused candidate | `NORMALIZATION` |
| P1-003 | transcript | university_name | candidates rejected by shape | `CANDIDATE_SELECTION` |
| P1-004 | transcript | student_name | no label observed | `OCR_RECOGNITION` |
| P1-004 | transcript | student_id | no label observed | `OCR_RECOGNITION` |
| P1-004 | transcript | university_name | label found, no value | `LABEL_VALUE_ASSOCIATION` |
| P1-004 | transcript | gpa | candidates rejected by shape | `COLUMN_STRUCTURE` |
| P1-004 | transcript | gpa_scale | candidates rejected by shape | `COLUMN_STRUCTURE` |
| P1-005 | enrollment | university_name | contaminated by adjacent column | `COLUMN_STRUCTURE` |
| P1-005 | enrollment | department | ranked path ties | `REPEATED_LABEL_AMBIGUITY` |
| P1-005 | enrollment | student_id | correctly absent per gold | `NONE` |
| P1-006 | enrollment | university_name | contaminated by adjacent column | `COLUMN_STRUCTURE` |
| P1-006 | enrollment | department | no label observed | `OCR_RECOGNITION` |
| P1-006 | enrollment | student_id | correctly absent per gold | `NONE` |

## Frequency, ranked

| Category | Fields | Share of 17 unresolved |
|---|---:|---:|
| `OCR_RECOGNITION` | **8** | 47% |
| `COLUMN_STRUCTURE` | 4 | 24% |
| `REPEATED_LABEL_AMBIGUITY` | 2 | 12% |
| `LABEL_VALUE_ASSOCIATION` | 2 | 12% |
| `CANDIDATE_SELECTION` | 1 | 6% |
| `NORMALIZATION` | 1 | 6% |
| Correctly abstained per gold | 2 | not counted |

Note that the P1-003 gpa entry is classified by *first* loss, which is shape
rejection; its underlying cause is also repeated-label ambiguity. Both are
recorded in `benchmark_summary.md`.

## The decisive measurement

Over the 17 fields P0 left unresolved:

| Label state | Count |
|---|---:|
| Label text **absent** from the OCR output | **8** |
| Label text **present** in the OCR output | 8 |
| Correctly absent per the gold | 1 |

**For 8 of 17 unresolved fields the label string simply is not in the OCR
output.** Examples, in each case the OCR read something adjacent instead:

- business registration number: OCR produced `사업자동록번호`
- company name: OCR produced `법인 영(단체영)`
- representative name: OCR produced `자:...`, having consumed the row above
- student id: OCR produced `학성 번:`
- department on an enrollment certificate: the document prints `소속`, which is
  not in the extractor's alias list

No column model, table model or layout architecture can recover a label string
that the recogniser did not produce. This is the single most important result of
P1 and it is why Architecture C was rejected despite being available.

## Column structure, precisely

On the second transcript the OCR detector emits **one box** containing

```
평점평균:3.50/4.0백분율:85.00/100
```

The grade-point cell and the percentage cell are inside a single bounding box.
There is no geometric boundary between them, because the detector did not draw
one. Column inference over the boxes that exist cannot split a string inside a
box. This is why column modelling produced **zero** additional correct fields
despite correctly identifying 5 to 16 column bands per page.

Recovering this case requires better *text detection granularity*, which is an
OCR/detector concern, not a layout concern.

## What the corpus does not exercise

Three supported document types are absent (graduation, career, national tax
payment), no document is born-digital, and no document is multi-page. Structural
failures typical of those cases are therefore **unmeasured**, not absent.