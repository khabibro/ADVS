# Pipeline Trace

Pipeline stages, in order:

```
document → render → preprocess → OCR detect → OCR recognise → observation
         → reading order → row construction → label match → candidate
         generation → candidate scoring → field resolution → normalisation
         → evidence creation → evidence policy → validation → review status
```

No failure below was inferred from the final `null`. Each one names the stage
where the information stops. All raw text stays in gitignored runtime storage.

## Stage health summary

| Stage | Verdict | Evidence |
|---|---|---|
| Document intake | healthy | 7/7 accepted, 7 pages, 0 rejects |
| Rendering | healthy but **provenance defect** | `metadata.render_dpi` misreports REAL-001 (288 vs actual 108) |
| Preprocessing | healthy | EXIF/codec conversion only; one WEBP converted, no upscaling anywhere |
| OCR detection | **healthy** | 0 confirmed failures; every human-readable value recovered page-wide |
| OCR recognition | **deficient** | 6 fields; 5 of them are short letter-spaced labels |
| Observation preservation | healthy | 650/650 observations carry a bounding box |
| Reading order | healthy | 7/7 pages reproduce byte-identical page text across runs |
| Row construction | **deficient** | merges the issuance date into unrelated rows on 2 documents |
| Label match | **deficient** | blocked by recognition errors on 5 fields, by alias gaps on 1 |
| Candidate generation | healthy where labels match | 1 candidate on every resolved field; 7 competing raw candidates on REAL-004 `gpa` |
| Candidate scoring | healthy | no wrong winner found; correct values won on all 16 resolved fields |
| Field resolution | healthy | no field resolved to a wrong value except the one recognition error |
| Normalisation | healthy | date, business-number and GPA formats all normalised correctly, including en dashes |
| Evidence creation | healthy | every produced field carries box + confidence + provenance |
| Evidence policy | healthy | every field on every document assessed `REVIEW_REQUIRED` or `UNAVAILABLE` |
| Validation | healthy | engine rules behave correctly on all 9 rule-level scenarios |
| Review status | healthy | 3–5 review items per document; human correction stays separate evidence |

---

## T1 — REAL-001 `business_registration_number` · RECOGNITION_FAILURE

- **Render** 108 DPI (scale 1.5, `source_resolution_fit`)
- **Detect** box present over the value
- **Recognise** value correct; **label** mis-transcribed — one character in
  the middle of a seven-syllable label (`자` → `동`)
- **Observation** survives with correct geometry
- **Rows** label, its parenthetical qualifier and the value are one row
- **Label match** the alias `사업자등록번호` requires that literal string; the
  OCR text does not contain it, so **no candidate is ever generated**
- **Resolution** field is `null`

The value was never lost. Only the label was, and the label is the key.

## T2 — REAL-002 `company_name` · RECOGNITION_FAILURE

- **Recognise** the label `법인명(단체명)` came back with two wrong characters
  and a word split; the value in the same box is correct
- **Label match** all four aliases (`법인명(단체명)`, `법인명칭`, `상호`,
  `상호명`) fail — the first because both characters are wrong, the others
  because this form prints no `상호`
- **Resolution** `null`

Note the extractor was *right* to try the statutory `법인명(단체명)` label
first; it lost only because the recognizer changed two characters of a
13-character label at 72 DPI.

## T3 — REAL-002 `representative_name` · RECOGNITION_FAILURE

- **Recognise** two independent errors: the label `대표자` lost its first two
  characters (only `자` survives), and the name's final character is wrong
  (character recall 2/3)
- **Label match** `대표자` absent → no candidate
- **Resolution** `null`

The label loss and the value loss are separate defects that happen to land on
the same field. Fixing only the label would still yield a wrong name.

## T4 — REAL-003 `student_name` · RECOGNITION_FAILURE — the wrong non-null

- **Detect** box present, correct position
- **Recognise** first character wrong (character recall 2/3); the other two
  characters are correct
- **Label match** `성명` recognised **correctly** — this is the one failure
  where the label is fine
- **Candidate generation** 1 candidate, produced via `spatial_right_of_label`
- **Scoring** 4 shape-valid candidates existed; the right one won
- **Resolution** a confident, non-null, **wrong** name
- **Evidence** 5 evidence refs, confidence 0.9166
- **Policy** `REVIEW_REQUIRED`
- **Review status** review item raised; remains gated

Full detail in `safety.md`.

## T5 — REAL-004 `student_id` · RECOGNITION_FAILURE

- **Recognise** the label `학번` came back as `학성` in one box and `번` in the
  next; the value is correct
- **Row construction** the two fragments are separate segments of the header row
- **Label match** the alias pattern tolerates whitespace *inside* a label, so
  `학 번` would have matched — but `학성` + `번` does not, because the
  substituted character sits between them
- **Resolution** `null`

A single wrong character in a 2-character label. There is no recovery path.

## T6 — REAL-004 `student_name` · RECOGNITION_FAILURE

- **Recognise** the label `성명` was absorbed into the previous field's box as a
  trailing `명:`; the value is correct
- **Label match** the alias `성명` needs to be preceded by a boundary or
  whitespace; inside `학성` it is not
- **Resolution** `null`

## T7 — REAL-001 `issue_date` · EXTRACTION_FAILURE

- **Detect / recognise** the date is correct. Two identical bare dates print.
- **Row construction** the first date *is* a date-only row
- **Inference check 1** all bare dates on the page agree → pass
- **Inference check 2** an issuer appears within 3 rows below → pass
  (`근로복지공단 귀하` matches the agency noun list)
- **Inference check 3** **FAILS** — the rule treats a bare date as owned by a
  preceding label. The preceding row is a boilerplate sentence that contains
  the token `발급일` as part of ordinary prose, so the rule concludes a
  date-label owns this date and abandons it.

The date was read correctly, passed two safety checks, and was then discarded
because a boilerplate sentence happened to contain a label-shaped word. The
refusal is *conservative* — the field is missing, not wrong — but it is a false
negative caused by prose, not by evidence.

## T8 — REAL-002 `issue_date` · EXTRACTION_FAILURE

- **Detect / recognise** the date is correct
- **Row construction** the seal glyph beside the date shares the same vertical
  band, so **no date-only row exists at all**
- **Inference** requires every bare date to normalise to one value; zero
  date-only rows means zero candidates, and the rule returns nothing

Cause: a stamp merged into the date's visual row. The same rule that safely
refuses ambiguity on REAL-001 refuses here for a reason that has nothing to do
with ambiguity.

## T9 — REAL-003 `issue_date` · EXTRACTION_FAILURE

- **Detect / recognise** the date is correct
- **Row construction** the issuance block overlaps the last course-table rows,
  so the date shares a row with course codes and grades
- **Inference** again no date-only row → no candidate

Cause: the signature block is vertically adjacent to a dense table. This is
purely a row-grouping outcome.

**T7, T8 and T9 are one symptom with three unrelated causes.** A count of
"3 broken issue dates" would have been true and useless.

## T10 — REAL-006 `department` · EXTRACTION_FAILURE

- **Recognise** the value is correct; `소속` was read, but as two boxes in two
  different rows, so the string `소속` never appears contiguously in the page
  text
- **Alias set** the enrollment extractor accepts only `학과` and `전공`.
  `소속` is **not** in the set
- **Row construction** the two label glyphs were grouped with the rows above and
  below rather than with each other
- **Resolution** `null`

Two independent defects, either of which alone is sufficient. The alias gap is
the one worth fixing and is discussed under overfitting in `final_report.md`.

## T11 — REAL-004 `gpa` and `gpa_scale` · STRUCTURAL_INTERPRETATION_FAILURE

- **Recognise** correct. Seven `평점평균` rows are read, plus the cumulative
  total row and its `/4.5` denominator
- **Candidate generation** 7 competing raw values; **0 survive shape
  validation**, because each candidate is the **entire summary cell** — the
  label, a grade point average, its scale denominator and a percentage, in one
  unbroken string — rather than a bare number. (The cell's exact text is
  private OCR output and stays in gitignored runtime storage.)
- **Resolution** `null`

The system cannot pick the cumulative row *and* cannot parse the cell it would
pick. Choosing between seven readings is a structural determination; parsing
the chosen cell is an extraction defect.

## T12 — REAL-004 / REAL-005 / REAL-006 `university_name` · STRUCTURAL_INTERPRETATION_FAILURE

- **No university label is printed anywhere on any of the three documents.**
  The name appears only as a letter-spaced signature line above an issuing
  officer's title
- **REAL-004** the line is read correctly; **REAL-005** it is read with one
  spurious mark; **REAL-006** one character is lost
- **Transcript path** a standalone-university fallback exists but requires a
  line to match end-to-end, and these lines end with an officer title
- **Enrollment path** there is no fallback at all
- **Resolution** `null` on all three

Resolving any of these requires knowing that a spaced line above a signature
names the issuing institution. That is block structure, not text.

## T13 — REAL-001 `valid_until`, REAL-005 `student_id` · SOURCE_ABSENT

The document prints a dash and no student number respectively. The frozen gold
records both as absent-by-design. `null` is the correct output. **These are not
defects and are excluded from the failure distribution.**

Note: REAL-001's `valid_until` is absent *and* the label `보험소멸일` is not in
that extractor's alias set, so it would not have been extracted even if
present. The right answer is reached for a partly wrong reason — recorded here
so it is not mistaken for validated coverage.

---

## Where the structural layer was tested

The dormant layer was run against the same observations, for the 9 fields where
OCR was already correct and the backend still failed.

| Generator | State | Candidates produced |
|---|---|---|
| `header_value_candidate` | active | **0 of 9** |
| `section_scoped_values` | hard-disabled, returns `[], 0` | 0 |
| `issuer_block_candidate` | hard-disabled, returns `None` | 0 |

**The structural layer resolved 0 of the 9 fields it was aimed at.** Column,
section and header structures were all derived successfully (up to 16 column
bands, 9 sections, 144 header/value pairs on REAL-003), so the geometry is
being computed — it simply does not produce a usable candidate for any failure
measured in this phase.

Two of its three generators are permanently disabled by prior P1 measurement,
documented in the code as negative results. So there is nothing here to
activate: the only live generator returns `None` on every case that matters.

## Loop closure check

Each failure was re-checked against the stage list above to confirm the
information really is gone at the named stage and not merely invisible at the
end. In all 13 traces the information is provably present in the OCR
observations; in no case did it disappear during rendering, preprocessing,
detection, observation storage or normalisation.
