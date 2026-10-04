# Architecture Analysis

## Strengths — genuinely good, and worth protecting

1. **The dependency direction is right.** `document_intelligence` owns OCR/classification/extraction/
   validation internals; `services` owns persistence and orchestration; routes are thin. No OCR
   internals leak into the API surface. This matches `.agents/architecture.md` and it holds in code.

2. **The abstention spine is real, not aspirational.**
   - Shape validation rejects impossible candidates → unresolved instead of wrong.
   - Candidate selection abstains when the strongest evidence class contains conflicting values.
   - `standalone_date_candidate` refuses when several bare dates exist or no issuer anchor is nearby.
   - Normalisers return `None` rather than guessing; a scalar date normaliser explicitly refuses a range.
   - `MIN_STRONG_SIGNAL_WEIGHT` stops SUPPORT/GENERIC-only keyword piles from asserting a type.
   - **Empirically: 0 hallucinated fields and 0 false READY across the whole evaluation.**

3. **Evidence is a first-class, truthful object.** Page, bbox, polygon, detection confidence,
   source kind, coordinate space and transform travel with every value. I confirmed the evidence for
   each populated field points at the row the value actually came from — including cases where the
   value is *wrong*, where the evidence is still *correct about what was read*. That distinction is
   the whole point and the system holds it.

4. **The evidence-sufficiency gate is the single best design decision here.** Marking every
   OCR-sourced value `REVIEW_REQUIRED` is what converts "3 confident wrong values" into "3 confident
   wrong values a human must confirm". Without it this system would be dangerous; with it, it is merely
   incomplete.

5. **Verification refuses to guess about configuration.** `RuleConfigurationError` is raised for any
   persisted rule the submission engine cannot evaluate safely, rather than silently skipping it. That
   single rule is what makes Phase 9 safe to start.

6. **Concurrency discipline in the data layer is thoughtful.** `acquire_project_lock` has a genuine
   SQLite workaround (a no-op UPDATE to take the write lock, because `SELECT … FOR UPDATE` is a no-op
   there). The atomic `UPDATE … RETURNING` claim for document processing is the right primitive.

7. **Staleness is handled end-to-end.** `processing_version`, review staleness, and a
   content-addressed input snapshot for verification. Adding a document to a READY project genuinely
   invalidates the decision — verified (J2).

8. **Null safety in verification is thorough and consistently correct.** `_supported_value` refuses
   review-marked fields and validates date syntax before any date comparison. Every null-safety probe
   I wrote passed.

## Weaknesses

1. **There is no structure layer.** This is the defining gap. The system has boxes and strings and no
   concept of a region, a cell, a column or a reading order beyond a crude y-band sort. Consequences
   measured:
   - the cleanest document in the set produced **0 of 6 fields** because a header band collapsed into
     one row and the labels were cross-merged;
   - GPA is unreachable on both transcripts;
   - a bare issue date merged with a stamp fragment, and the issuer-anchor lookahead missed.

2. **Recogniser confidence is treated as a number worth showing.** The policy code is careful and says
   in comments that confidence is not correctness probability — and then the pipeline persists and
   surfaces `0.9955` for a value that is wrong. The policy is right; the presentation is not.

3. **Resource model is wrong-shaped.** One OCR thread, one permit, and a 120-second budget for the
   *whole document*. That combination makes multi-page documents impossible and turns ordinary
   concurrent use into a terminal `FAILED` state.

4. **Two field vocabularies.** `EXPECTED_FIELDS` (authorises review, defines required fields) and what
   the extractors actually emit have drifted apart. This makes 10 field/document combinations
   unresolvable by a human and keeps document-scope status permanently open.

5. **Two comparison semantics for the same job** inside one product, one permissive and one exact.

6. **Heuristics are tuned by assumption.** Several are demonstrably wrong on real documents, and two
   of them (`issue_date_field`'s page-wide guard, the SME label order) have an already-fixed twin in a
   sibling file — the fix was found once and not propagated.

7. **Third-party global state is trusted.** Paddle mutates the root logger, permanently disabling the
   application's own audit trail.

8. **Layering leak in storage validation.** The storage service imports OCR render DPI to pre-compute a
   raster budget, which (a) duplicates a check the OCR provider already performs, and (b) rejects a
   legitimate document by 0.65 %.

## Heuristic debt inventory

| Heuristic | Value | Why it exists | Tested? | Generalises? | Can it cause a wrong value? | Verdict |
|---|---|---|---|---|---|---|
| `_RETRY_MIN_CHARS_PER_PAGE = 120` | F-18 | orientation trigger | yes | **no** (fires on any sparse upright page) | no | make confidence-only |
| `_ISSUANCE_ANCHOR_LOOKAHEAD = 3` | F-09 | issuance-block detection | yes | **no** (dense transcripts) | no | make distance-based |
| `DEFAULT_OVERLAP_RATIO = 0.5` | F-05, F-08 | row grouping | yes | **no** (no gap/height/extent limit) | no (causes nulls, not wrong values) | keep, add gap + extent caps |
| `_Y_BAND_PX = 12.0` | reading order | reading order | yes | mostly | no | keep |
| `_MAX_LABEL_SEGMENTS = 5` | F-05 | letter-spaced labels | yes | yes | no | keep |
| `AMBIGUITY_MARGIN = 1.0` | — | classification abstention | yes | reasonable | no | keep |
| `MIN_STRONG_SIGNAL_WEIGHT = 3.0` | — | prevents weak-label assertion | yes | yes | no | keep |
| `MIN_SCORE_FOR_CONFIDENT_TYPE = 1.0` | — | type floor | yes | yes | no | keep |
| `minimum_ocr_field_confidence = 0.90` | — | review floor | yes | **never decisive** — every OCR value is gated anyway | n/a | keep, but note it is dead weight today |
| `paddle_ocr_render_dpi = 288` | F-01, F-14 | recognition quality | yes, measured | yes for OCR; **no** for the pixel budget | no | keep the DPI; fix the budget coupling |
| Label-list ordering per extractor | F-04 | compound labels | **no** | **no** | yes (via wrong-abstention) | fix + add a shadowing test |
| `issue_date_field` label guard | F-03 | avoid double-claiming | yes | **no** | no | **fix** |
| `shape_candidate` weights (length penalty, row index) | — | ranking | yes | partly | **yes** — rank decides which wrong value wins | keep; the conflict guard is the real protection |
| `_right_associated` gap ≤ 12·h | — | label/value geometry | yes | reasonable | no | keep |
| `_BOILERPLATE_MARKERS` | F-08 | drop chrome | yes | narrow by design | no | keep |

## Keep / Improve / Replace

| Component | Decision | Evidence | Reason | Risk if changed |
|---|---|---|---|---|
| OCR provider adapter | **IMPROVE** | works on real Korean scans; 88 % line-level model; F-06/F-10/F-11 | correct abstraction, wrong inputs | low |
| **Layout/table structure** | **ADD** | F-05, F-07, F-08; transcripts at 0/6 and 3/6 | the missing layer | medium |
| OCR representation (lines+bbox+polygon+conf+source) | **KEEP** | evidence truthful on every populated field | it is correct | high |
| Row grouping | **IMPROVE** | header band collapsed into one 7-segment row | add gap/extent caps; do not replace | medium |
| Classification | **IMPROVE** | 6/6 here but never abstained; keyword heuristic | add document-level features + negative examples | low |
| Document-specific extractors | **IMPROVE** | F-04; transcript's standalone fallback is missing from enrollment | cheap, targeted | low |
| Base extractor | **IMPROVE** | F-03; unranked legacy date/gpa helpers bypass shape validation | one guard is wrong; legacy path should converge on the ranked path | medium |
| Candidate generation | **IMPROVE** | F-03, F-04 | | low |
| Candidate ranking | **KEEP** | conflict-abstains guard prevented a wrong GPA (3.5 vs 4.12) | it is the safety net | high |
| Normalisation | **KEEP** | 56/57 probes pass | conservative and correct | high |
| Evidence model | **IMPROVE** | truthful; but `detection_confidence`, `polygon`, `transform` are persisted and unused, and `results._evidence_from_dict` is lossy | make consumers, or drop the unused fields | low |
| Confidence policy | **IMPROVE** | policy correct, presentation misleading; the 0.90 floor is dead weight | present reasons, not numbers | low |
| Human review | **IMPROVE** | all four decisions verified; 10 combos unreachable | vocabulary fix | low |
| Effective-field resolver | **KEEP** | exactly right | | high |
| Submission verification engine | **KEEP** | deterministic, null-safe, refuses unsafe config | | high |
| Workflow / status aggregation | **KEEP** | 0 false READY in 8 scenarios | | high |
| Document-scope validation net | **IMPROVE** | never closes for OCR documents; scope it to required fields | | medium |
| Comparison semantics | **IMPROVE** | two semantics, one product | unify | medium |
| Storage validation | **IMPROVE** | F-01 layering leak | | low |
| OCR resource model | **REPLACE** | F-13, F-14 | single-thread + per-document timeout is the wrong shape | medium |
| Logging | **IMPROVE** | F-15 one-line fix | | very low |
| Persistence / migrations | **KEEP** | head reached, all migration tests pass | | high |
| Contract generation | **KEEP** | `openapi.json` + generated TS types in sync | | low |

## Recommended target architecture

**Not a rewrite.** The deterministic spine — evidence → policy → review → effective → rules → status —
is correct and should not be touched. Three additive changes:

1. **Insert a structure stage between the OCR provider and the extractors.**
   `PaddleOCRProvider` gains an optional layout pass (`PP-StructureV3` with layout detection +
   `SLANeXt_wired` table structure). It returns region types and, for tables, a cell grid with cell
   polygons. `_source_observations` then yields both `TextRow`s *and* `TableCell`s; the existing row
   path stays as a fallback for non-table regions. Extractors gain one capability: a cell can be
   addressed by (row, column) as well as by label adjacency. **Same recogniser, one extra layer.**
   This is the change that makes transcripts work.

2. **Replace the synchronous OCR resource model with a queued job.**
   `/process` claims the row, enqueues, and returns; a worker drains the queue. The budget becomes
   per-page, not per-document. `OCR_BUSY` and `OCR_TIMEOUT` stop being terminal states because there
   is no longer a "second caller" to fail — there is a queue. This also makes the capstone demo
   survive a user clicking twice.

3. **Make the review vocabulary single-sourced and scope the document net.**
   `EXPECTED_FIELDS` becomes the one vocabulary that extractors, reviewers and required-field defaults
   derive from, enforced by a test that asserts
   `set(extractor fields) ⊆ EXPECTED_FIELDS[type]`. Document-scope `MISSING_REQUIRED_FIELD` is scoped
   to the workflow's required fields.

Optional fourth, later: a **semantic fallback** that may *propose* a candidate with explicit
low-trust provenance, which the existing gate would route to human review. It may never become
authoritative. Explicitly **not** recommended now: the measured bottleneck is structure and
resolution, and a VLM would trade away the determinism that is ADVS's entire differentiator.