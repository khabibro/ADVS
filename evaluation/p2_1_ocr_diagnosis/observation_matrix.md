# Observation Matrix

One row per annotated field. **No private value appears in this file** — only
safe IDs, field names and categorical judgements.

Column meanings:

- **Visible** — a human can see a value for this field on the page.
- **Readable** — a human can read it at the document's own resolution.
- **OCR box** — whether the detector produced an observation carrying that
  value. `elsewhere` means it was found on the page but not at its own
  position; `wrong text` means glyphs were detected but transcribed wrongly.
- **OCR text** — whether the recognised characters convey the value.
- **Extraction** — what the production extractor produced for the field.
- **Label in aliases** — whether the extractor's alias set for this field
  contains the label the document prints.

## Matrix

| Doc | Field | Visible | Readable | OCR box | OCR text | Extraction | Label in aliases | Diagnosis |
|---|---|---|---|---|---|---|---|---|
| REAL-001 | `business_registration_number` | YES | YES | YES | CORRECT | none | yes | **RECOGNITION_FAILURE** |
| REAL-001 | `issue_date` | YES | YES | YES | CORRECT | none | no label printed | **EXTRACTION_FAILURE** |
| REAL-001 | `valid_until` | YES | YES | n/a | n/a | none | NO | **SOURCE_ABSENT** |
| REAL-001 | `workplace_name` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-002 | `business_address` | YES | no | n/a | n/a | n/a (not in gold) | yes | **NOT_EVALUATED** |
| REAL-002 | `business_registration_number` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-002 | `company_name` | YES | YES | YES | CORRECT | none | yes | **RECOGNITION_FAILURE** |
| REAL-002 | `issue_date` | YES | YES | YES | CORRECT | none | no label printed | **EXTRACTION_FAILURE** |
| REAL-002 | `representative_name` | YES | YES | YES (wrong text) | INCORRECT | none | yes | **RECOGNITION_FAILURE** |
| REAL-003 | `gpa` | YES | YES | n/a | n/a | none | yes | **NOT_EVALUATED** |
| REAL-003 | `gpa_scale` | YES | no | n/a | n/a | none | NO | **NOT_EVALUATED** |
| REAL-003 | `issue_date` | YES | YES | yes (elsewhere) | not at position | none | no label printed | **EXTRACTION_FAILURE** |
| REAL-003 | `student_id` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-003 | `student_name` | YES | YES | YES (wrong text) | INCORRECT | WRONG NON-NULL | yes | **RECOGNITION_FAILURE** |
| REAL-003 | `university_name` | YES | YES | YES | CORRECT | CORRECT | no label printed | **NONE** |
| REAL-004 | `certificate_number` | YES | YES | n/a | n/a | none | n/a | **NOT_EVALUATED** |
| REAL-004 | `department` | YES | YES | YES (wrong text) | INCORRECT | none | n/a | **NOT_EVALUATED** |
| REAL-004 | `gpa` | YES | YES | YES | CORRECT | none | yes | **STRUCTURAL_INTERPRETATION_FAILURE** |
| REAL-004 | `gpa_scale` | YES | YES | YES | CORRECT | none | yes | **STRUCTURAL_INTERPRETATION_FAILURE** |
| REAL-004 | `issue_date` | YES | YES | YES | CORRECT | CORRECT | no label printed | **NONE** |
| REAL-004 | `student_id` | YES | YES | YES | CORRECT | none | yes | **RECOGNITION_FAILURE** |
| REAL-004 | `student_name` | YES | YES | YES | CORRECT | none | yes | **RECOGNITION_FAILURE** |
| REAL-004 | `university_name` | YES | YES | YES | CORRECT | none | no label printed | **STRUCTURAL_INTERPRETATION_FAILURE** |
| REAL-005 | `department` | YES | YES | yes (elsewhere) | not at position | none | yes | **NOT_EVALUATED** |
| REAL-005 | `issue_date` | YES | YES | YES | CORRECT | CORRECT | no label printed | **NONE** |
| REAL-005 | `student_id` | NO | no | n/a | n/a | none | yes | **SOURCE_ABSENT** |
| REAL-005 | `student_name` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-005 | `university_name` | YES | YES | YES (near) | near-correct | none | no label printed | **STRUCTURAL_INTERPRETATION_FAILURE** |
| REAL-006 | `department` | YES | YES | YES | CORRECT | none | NO | **EXTRACTION_FAILURE** |
| REAL-006 | `issue_date` | YES | YES | YES | CORRECT | CORRECT | no label printed | **NONE** |
| REAL-006 | `student_id` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-006 | `student_name` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-006 | `university_name` | YES | YES | YES | CORRECT | none | no label printed | **STRUCTURAL_INTERPRETATION_FAILURE** |
| REAL-007 | `business_address` | YES | no | n/a | n/a | none | n/a | **NOT_EVALUATED** |
| REAL-007 | `business_registration_number` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-007 | `certificate_number` | YES | YES | n/a | n/a | n/a (not in gold) | yes | **NOT_EVALUATED** |
| REAL-007 | `company_name` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-007 | `issue_date` | YES | YES | YES | CORRECT | CORRECT | no label printed | **NONE** |
| REAL-007 | `representative_name` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-007 | `valid_from` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |
| REAL-007 | `valid_until` | YES | YES | YES | CORRECT | CORRECT | yes | **NONE** |

## Aggregate

33 gold-evaluated fields (matching the frozen scorer's denominator exactly),
plus 8 fields outside the frozen gold.

| Diagnosis | Count | Share of 33 evaluated |
|---|---|---|
| NONE (no failure) | 16 | 48.5% |
| RECOGNITION_FAILURE | 6 | 18.2% |
| STRUCTURAL_INTERPRETATION_FAILURE | 5 | 15.2% |
| EXTRACTION_FAILURE | 4 | 12.1% |
| SOURCE_ABSENT | 2 | 6.1% |
| **DETECTION_FAILURE** | **0** | **0.0%** |
| ASSOCIATION_FAILURE | 0 | 0.0% |
| SOURCE_UNREADABLE | 0 | 0.0% |
| AMBIGUOUS | 0 | 0.0% |

Of the **17 failures**:

| Category | Count | Share of failures |
|---|---|---|
| Recognition | 6 | 35.3% |
| Structural interpretation | 5 | 29.4% |
| Extraction path | 4 | 23.5% |
| Source absent (not a defect) | 2 | 11.8% |
| **Detection** | **0** | **0.0%** |

## Detection measurement

| Value detection outcome | Count |
|---|---|
| Observed, at its own position | 26 |
| Observed elsewhere on the page | 1 |
| All characters present, text near-correct | 1 |
| Detected but mis-transcribed | 2 |
| **Not observed at all** | **0** |
| Not applicable (no gold value) | 2 |

**Read this correctly:** "0 confirmed detection failures" means the evidence
did not confirm any. It does **not** mean detection is perfect. The bound on
this claim is stated in `failure_taxonomy.md`.

## What the matrix shows

Three patterns, and they matter more than the totals.

**Labels are the weak point, not glyphs.** In 5 of the 6 recognition failures
the *value* was read perfectly and the *label* was misread — `사업자등록번호`
→ `사업자동록번호`, `법인명(단체명)` → `법인 영(단체영)`, `대표자` → `자`,
`학번` → split as `학성`+`번`, `성명` → split as `학성`+`명`. A label is short,
letter-spaced on these forms, and carries no redundancy, so a single
character error destroys the alias match while leaving the value intact.

**Three different causes produce one symptom.** All three failed issue dates
are byte-for-byte the same kind of failure — a correct date that produced no
field — and the trace shows three unrelated mechanisms behind them. A single
"issue dates are broken" observation would have hidden all three.

**Two fields are not defects.** REAL-001 `valid_until` and REAL-005
`student_id` are `SOURCE_ABSENT`: the document prints a dash and no student
number respectively. Producing a value there would be wrong. These are counted
separately so they cannot inflate or deflate the failure rate.
