# P2.1 Gold Adjudication

Adjudication of the three gold annotations flagged as questionable in
`final_report.md` §F.2. Scope is limited to these three fields. No other
field, no OCR, no extraction logic, no structural layer, and no production
code was touched. Nothing was committed or pushed.

Method: for each field, the frozen gold value/state was treated as a
hypothesis, not a fact. Evidence was read directly from the rendered
document page (via existing zoomed crops of the unchanged original image —
no new OCR run, no new rendering), cross-checked against the actual
production field definition in code, and only then compared against OCR
output as corroboration, never as the basis for a decision.

## REAL-003 / gpa_scale

- **Previous state:** `NOT_EVIDENCED`
- **Adjudicated state:** `KNOWN_VALUE`
- **Decision:** Changed
- **Evidence type:** Direct visual inspection of the document's own printed
  cumulative-GPA cell (primary), corroborated by a separate printed
  letter-grade legend elsewhere on the page (secondary), corroborated by OCR
  text at both locations (tertiary, not decision-bearing).
- **Reason:** The production field definition (`gpa_field` /
  `gpa_scale_field` in `apps/api/app/document_intelligence/extraction/base.py`,
  and `normalize_gpa_scale` in `normalization/field_normalizer.py`) defines
  `gpa_scale` as the denominator parsed from the *same* candidate text as
  `gpa` — a `"score/scale"` pattern following the GPA label, not any general
  grading-conversion table. The document's cumulative-total cell prints
  exactly that pattern, so the scale is directly evidenced by the same cell
  used to adjudicate `gpa` below. A separate, fully-labelled letter-grade
  legend is also printed elsewhere on the page and independently states the
  same scale — this is consistent corroboration, but was deliberately *not*
  used as the primary basis, because a general grading legend is a different
  semantic object from "the scale of this transcript's GPA figure," and
  treating it as interchangeable is exactly the OCR-evidence-vs-ground-truth
  conflation this phase was told to avoid. The previous `NOT_EVIDENCED`
  annotation was correct that one specific nearby string (a historical
  maximum figure) does not establish a scale — but a different, better piece
  of evidence was available on the same page and was missed.
- **Confidence:** High. The deciding evidence is an explicit printed
  fraction in the same cell as the adjudicated `gpa` value, legible at
  moderate zoom, matching the exact pattern the field extractor parses.
- **Impact on denominator:** +1 (moves from not-evaluated to evaluated).

## REAL-004 / department

- **Previous state:** `AMBIGUOUS` (with an attached value)
- **Adjudicated state:** `AMBIGUOUS` (value removed)
- **Decision:** Changed (value only; state retained)
- **Evidence type:** Direct visual inspection of the document's header
  block, corroborated by OCR text at the same location.
- **Reason:** The previously recorded value does not appear anywhere on the
  page, in any observation — confirmed by direct inspection, not merely by
  OCR's failure to find it (the applicable safety rule: absence of a value
  must be established positively, not inferred from OCR silence). Per
  instruction, an unsupported value was removed rather than replaced with a
  manufactured one. The `AMBIGUOUS` state itself is retained and remains
  independently correct: the document prints two different
  department-like strings under two different labels, and the document does
  not state which one the `department` field is meant to capture.
  **Separate finding, not a gold-state change:** the production field schema
  (`EXPECTED_FIELDS[DocumentType.TRANSCRIPT]` in
  `apps/api/app/core/domain.py`) does not include a `department` field at
  all for transcripts — only `student_name`, `university_name`,
  `student_id`, `issue_date`, `gpa`, `gpa_scale`. REAL-003, the other
  transcript in this corpus, carries no `department` gold entry. So this
  field is not evaluated for transcript-type documents in production
  regardless of its gold state, independent of the page-level ambiguity
  above. This is flagged for a human product decision (should `department`
  be a transcript field at all, and if so which label); the field schema
  was not changed, per instruction not to silently change production
  schemas.
- **Confidence:** High on the value removal (the string is absent from the
  page, directly confirmed). The underlying ambiguity itself remains
  unresolved by design — that is the correct outcome, not a gap in this
  adjudication.
- **Impact on denominator:** 0 (stays not-evaluated, for two independent
  reasons: document-level ambiguity, and schema inapplicability).

## REAL-003 / gpa

- **Previous state:** `AMBIGUOUS`
- **Adjudicated state:** `KNOWN_VALUE`
- **Decision:** Changed
- **Evidence type:** Direct visual inspection of the document's header
  summary block, corroborated by OCR text at the same location, corroborated
  by an identical annotation convention already applied elsewhere in this
  same gold file.
- **Reason:** The document prints an explicitly labelled cumulative/overall
  totals row in its header summary block — four adjacent columns, each
  column header carrying the same "total" prefix character, with the
  rightmost GPA-bearing column printing a `"score/scale"` fraction. This is
  distinct from, and does not require counting or inferring from, the
  repeated per-semester GPA figures that justified the original `AMBIGUOUS`
  call — an explicit "total" row is categorically different evidence from a
  repeated per-term value, because its own label states that it aggregates
  across terms rather than repeating one. The same resolution rule (use the
  cumulative/total-credit summary row, not a semester occurrence) is already
  the recorded convention for the *other* real transcript in this same gold
  file, so this decision does not introduce a new rule — it corrects an
  inconsistency where one of two structurally similar documents had the rule
  applied and the other did not.
- **Confidence:** High. Exactly one row on the page carries an explicit
  "total" label; no second candidate is similarly labelled.
- **Impact on denominator:** +1 (moves from not-evaluated to evaluated).

## Field definitions consulted

- `apps/api/app/core/domain.py` — `EXPECTED_FIELDS`, confirms per-document-type
  field schema (used for the `department` finding above).
- `apps/api/app/document_intelligence/extraction/transcript.py` — confirms
  `gpa` and `gpa_scale` are extracted from the same label set and the same
  candidate text.
- `apps/api/app/document_intelligence/extraction/base.py` — `gpa_field`,
  `gpa_scale_field`: both call `candidate_after_label()` on the same labels;
  `gpa_scale_field` parses the denominator of that same candidate.
- `apps/api/app/document_intelligence/normalization/field_normalizer.py` —
  `normalize_gpa`, `normalize_gpa_scale`: both match the same `"score/scale"`
  regex against the same candidate text; `gpa_scale` is literally defined as
  that match's second group.

No field, extraction, or normalization code was modified during this
inspection.

## Denominator

- **Old denominator:** 33
- **New denominator:** 35
- Two fields (`REAL-003/gpa`, `REAL-003/gpa_scale`) moved from
  not-evaluated to evaluated. `REAL-004/department` remains not-evaluated,
  for two independent reasons (page-level ambiguity, and — newly
  identified — schema inapplicability to the `TRANSCRIPT` document type).

## Gold version

- **gold_v1 (this adjudication's baseline):**
  `evaluation/backend_round2/work/ground_truth_v2.json` — unmodified,
  preserved, `sha256:218ac059ed117403022bbae6035eb056613d26e46180a7670bb2201626e17107`.
  This is the file that was frozen and read (not edited) throughout P2.1.
- **gold_v2 (this adjudication's output):**
  `evaluation/backend_round2/work/ground_truth_v3.json` — created new, does
  not overwrite v2. Contains exactly three changed field records
  (`R2-03.gpa`, `R2-03.gpa_scale`, `R2-04.department`) against the v2
  baseline; every other sample and field is unchanged. `parent_gold_sha256`
  records the v2 hash it was derived from. Both files, and the private
  document images and crops used as evidence, live under the gitignored
  `evaluation/backend_round2/work/` and `evaluation/private_runtime/`
  directories and are not tracked by git.
- **Result: `GOLD_V2_CREATED`** (two field states changed, one value-only
  correction; see Outcome C in the task framing).

## Historical metric handling

The historical P2.1 numbers (`final_report.md`, `failure_taxonomy.md`,
`observation_matrix.md`, field recall 0.4706, wrong non-null 1, etc.) are
**unchanged and untouched**. They remain the P2.1-original result, scored
against the 33-field gold (v2).

A **P2.1 corrected-gold interpretation** is recorded separately, here: with
gold v3, the evaluated-field denominator is 35, not 33. No field recall,
precision, or failure-taxonomy figure has been recomputed against v3 in this
phase — recomputing those requires re-running the same observation-matrix
scorer used in P2.1, which is a scoring action, not an adjudication action,
and is explicitly out of scope here (see "Do not re-score production yet").
That re-scoring is left for the next phase to do deliberately, against a
gold version that is now frozen.

## Pre-existing condition noted, not adjudicated

`R2-07/department` (not one of the three fields in scope here) carries an
`AMBIGUOUS` state with a non-null attached value, which is inconsistent with
this gold file's own convention elsewhere (`AMBIGUOUS` entries otherwise
carry `value: null`, e.g. `R2-03/gpa` before this adjudication). This
predates this phase, was not introduced by it, and was left untouched
because it falls outside the three fields named in scope. Flagged here so it
is not lost before a future adjudication pass.

## Production code

Production code was not changed. No OCR setting was changed. No extraction
logic was changed. The structural layer was not activated. Nothing was
committed or pushed.
