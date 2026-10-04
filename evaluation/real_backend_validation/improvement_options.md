# Improvement Options — proposal only, NOT implemented

Nothing in this document was implemented during the audit. The baseline was frozen first, and these
are the outputs of that analysis.

---

## P0 — correctness and safety

### P0-1 · Decouple the OCR timeout from the worker (F-14, F-13) — CRITICAL
- **Problem:** `ocr_timeout_seconds=120` bounds the whole document while a dense A4 page costs ~25.4 s. Measured 1p=25.7 s OK, 3p=76.3 s OK, **6p FAILS at 120.0 s**. `max_pdf_pages=30` is unreachable. A timeout keeps the single worker occupied, so the next request also fails `OCR_BUSY`, and `OCR_BUSY` becomes a terminal `FAILED` document.
- **Evidence:** live HTTP + direct provider measurement, reproducible.
- **Root cause:** per-document budget on a synchronous single-thread worker.
- **Proposed solution (primary):** queue-based processing. `/process` claims the row (`UPDATE … RETURNING`, already implemented), enqueues, returns 202; a single worker drains the queue. Budget becomes per-page. `OCR_BUSY` disappears as a terminal state; a second submission waits instead of failing.
- **Interim solution if a queue is too large right now:** (a) raise `ocr_timeout_seconds` and scale it with page count (`base + per_page × n`), (b) reduce `paddle_ocr_render_dpi` for documents over N pages, (c) stop `_fail`-ing on `OCR_BUSY` — leave the row claimable and return a retryable outcome.
- **Alternatives:** a process pool (rejected — Paddle engine construction cost and the shared-model model directory make it heavy for a capstone); a per-request timeout with client-side retry (rejected — leaves the document in a half-state).
- **Files:** `app/services/processing.py`, `app/document_intelligence/ocr/worker.py`, `app/api/v1/routes.py`, `app/core/config.py`.
- **Tests:** single-page succeeds; 3-page succeeds; 6-page succeeds or returns a *retryable*, not terminal, state; two concurrent submissions both complete; `max_pdf_pages` documentation matches measured capacity.
- **Regression risk:** low. `_fail` semantics change only for `OCR_BUSY`/`OCR_TIMEOUT`.
- **Benefit:** makes the actual product use case (multi-document, multi-page packs) possible at all.

### P0-2 · Fix the page-wide label guard in `issue_date_field` (F-03) — HIGH
- **Problem:** `issue_date` is null on 3 of 6 documents. The guard
  `any(re.search(_label_pattern(label), source_text(text)) for label in labels)`
  substring-matches the **entire page**; the standard Certipia footer contains the issue-date label plus
  a suffix, so the guard fires and the working `standalone_date_candidate` is never consulted.
- **Evidence:** minimal reproduction — identical document returns the correct date with the footer
  removed and `None` with it present.
- **Root cause:** document-scoped test where row-scoped semantics are required.
- **Proposed solution:** treat a label as "present" only when it terminates a row that carries no value,
  evaluated over `_source_observations` (which already know the label-vs-value distinction and carry
  the boilerplate filter), never over the flattened page text.
- **Alternatives:** strip boilerplate rows before the guard (simpler, less precise); allow
  `standalone_date_candidate` to override a *boilerplate-sourced* label match (fastest, weakest).
- **Files:** `app/document_intelligence/extraction/base.py`.
- **Tests:** the three reproduced documents return the correct date; a document with a genuine labelled
  `발급일자` still prefers the label; a document with `발급일로부터` only in the footer uses the
  standalone path; a document with two conflicting bare dates still abstains.
- **Regression risk:** low-medium — it *widens* the standalone path, so re-run the abstention tests to
  confirm they still abstain.
- **Benefit:** unlocks the student workflow's only configured rule on 3 of 6 documents. Cheapest
  high-value fix in the system.

### P0-3 · Fix label shadowing across extractors (F-04) — MEDIUM/HIGH
- **Problem:** `SMEConfirmationExtractor.representative_name` passes `['대표자','대표자명']`; the short
  label matches inside the compound one, leaves `명: <name>` as the value, fails PERSON_NAME shape
  validation, and the matcher breaks out of the label loop. Verified: wrong order → `None`; right
  order → correct value.
- **Evidence:** minimal reproduction; a live document loses a readable field.
- **Root cause:** order-dependent label lists plus a matcher that gives up on the first invalid candidate.
- **Proposed solution:** (a) sort labels longest-first at every call site, and (b) change the matcher to
  *try all labels of the field* and rank the surviving candidates instead of breaking. Then add a
  static test that asserts no label list contains a label that is a proper prefix of a later label.
  Three remain today: `SME.representative_name`, `BR.company_name`, `BR.representative_name`.
- **Alternatives:** only reorder the lists (fastest; leaves the latent bug class).
- **Files:** `sme_confirmation.py`, `business_registration.py`, `extraction/base.py`, `tests/`.
- **Tests:** the reproduced row resolves; the shadowing static test; per-extractor coverage asserting
  every canonical field of every document type has at least one extraction path.
- **Regression risk:** medium — ranking across all labels could change which candidate wins; the
  conflict-abstains guard bounds the damage.
- **Benefit:** removes an entire bug class that has already been found and fixed once, in a sibling file.

### P0-4 · Restore the structured audit trail (F-15) — MEDIUM
- **Problem:** the deployed server emits no per-stage records. PaddleOCR model construction sets the
  **root** logger to WARNING; ADVS's JSON handler is on the root logger, so every record after the first
  OCR call is dropped. Verified: a successful process emitted 1 record instead of 6.
- **Evidence:** root-logger snapshot around one OCR call: `INFO → WARNING`, handler still attached,
  stderr writable, no logging error. Confirmed on the live server.
- **Root cause:** trusting global logging state against a native dependency.
- **Proposed solution:** `configure_logging` attaches a handler to the `app` logger with
  `propagate=False` (or re-asserts the root level after engine construction).
- **Alternatives:** a `logging.Filter` on the root handler (weaker).
- **Files:** `app/core/logging.py`.
- **Tests:** a test asserting `app` INFO records reach the handler after a simulated engine build;
  assert the six processing records exist for a successful process.
- **Regression risk:** very low.
- **Benefit:** restores per-page source provenance in logs. Without it, neither this audit nor an
  on-call engineer can diagnose extraction failures. Prerequisite for operating Phase 9.

### P0-5 · Make the repository's own gate green — HIGH
- **Problem:** `pytest` fails 2/340. One is a real-document regression test written for exactly the
  REAL-007 department case and left red; one is schema drift on a required `processing_version`.
  `ruff format --check` also fails on 3 files (not part of `make check`).
- **Proposed solution:** make the department test pass using P0-3's mechanism (prefer the primary major
  over the double major — the test documents the intended behaviour and the current code abstains);
  update the schema test; add `ruff format --check` to `make check`.
- **Tests:** the two existing tests; plus `make check` end-to-end.
- **Benefit:** no new code should merge while the gate is red. Also: the red department test is
  independent corroboration of my REAL-007 finding, so it should be treated as a bug report, not noise.

---

## P1 — realistic extraction reliability

### P1-1 · Single-source the field vocabulary (F-16) — HIGH
Reconcile `EXPECTED_FIELDS` with extractor output so no field can be produced without being reviewable;
scope document-scope `MISSING_REQUIRED_FIELD` to the workflow's required fields.
**Tests:** a static test asserting `set(extractor fields) ⊆ EXPECTED_FIELDS[type]` for all 8 types; a
test that a fully-reviewed document can reach a closed document status.
**Risk:** medium — changes which fields count as required.
**Benefit:** removes 10 unresolvable field/document combinations; removes a permanently-open status.

### P1-2 · Decouple the pixel budget from the OCR render DPI (F-01) — HIGH
Stop projecting `paddle_ocr_render_dpi` in the storage layer. Keep the per-page guard where the raster
is produced (already in `PaddleOCRProvider._check_pixels`); bound the document with the existing
cumulative `max_pdf_render_pixels`. Keep `max_image_pixels` for *decoded uploads*.
**Tests:** the oversized-page document uploads; a genuinely huge decoded image is still rejected; a
30-page PDF still hits `TOO_MANY_PAGES`.
**Risk:** low.

### P1-3 · Unify comparison semantics (F-17) — MEDIUM
One comparison helper for document scope and submission scope. Given the pre-check product position,
the whitespace/punctuation-insensitive semantics is correct. Record the raw and compared forms in the
issue so the reviewer sees what was ignored.
**Tests:** two company names differing only by a space compare equal; genuinely different names still
mismatch; the mismatch issue carries both forms.

### P1-4 · Bound row merging; make the issuance anchor distance-based (F-08, F-09) — MEDIUM
Add an inter-segment horizontal-gap cap and a height-ratio condition to `build_rows`; add a horizontal
extent cap so a wide band cannot collapse into one row. Replace
`_ISSUANCE_ANCHOR_LOOKAHEAD = 3` with a bounded vertical-distance scan of the remaining rows on the page.
**Tests:** the REAL-002 and REAL-003 date rows resolve; multi-line body text is still not collapsed;
cross-page anchoring is still refused; letter-spaced labels still group.
**Risk:** medium — row grouping underpins everything; this needs the realistic corpus to guard it.

### P1-5 · Build a trustworthy realistic corpus — HIGH (enabling everything else)
At least 30 real documents across all 8 types + real UNKNOWN inputs, ≥3 multi-page, ≥2 low-resolution,
independent human ground truth (not an agent reading its own OCR), and a **provenance class on every
sample** (`REAL` / `RECREATED` / `SYNTHETIC`) reported separately. Also: fix F-02 by removing or
relabelling the synthetic specimen currently presented as realistic.
**Note on the two scorers:** `eval_lib/metrics.py` iterates gold keys only, so hallucinated fields are
invisible, and it scores `gold None == pred None` as "correct", conflating abstention with correctness.
`eval_lib/safety.py` is materially better. **Consolidate on the better semantics** and report
unlabelled-populated fields as wrong, not merely as `NOT_EVALUATED`.

---

## P2 — architecture

### P2-1 · Add a layout / table-structure stage — HIGHEST LEVERAGE
`PaddleOCRProvider` gains an optional PP-StructureV3 layout pass with `SLANeXt_wired` table structure
recognition. It returns region types and a cell grid with cell polygons. `_source_observations` yields
both `TextRow`s *and* `TableCell`s; the row path remains the fallback for non-table regions.
Extractors gain the ability to address a cell by (row, column) as well as by label adjacency.
**Same recogniser. One extra layer.** Unlocks transcripts (0/6 and 3/6 today) and the ruled form.
**Tests:** the two transcripts gain GPA/student metadata; the ruled form's table cells are recovered;
non-table certificates are byte-identical to today's output (proves no regression);
`EXTRACTOR_VERSION` is bumped so results are not silently mixed.
**Risk:** medium — new dependency, new failure modes, higher latency per page (which interacts with
P0-1; **do P0-1 first**).
**Benefit:** the largest measured capability gap, closed without touching the deterministic spine.

### P2-2 · Per-field corroboration signals — MEDIUM
For identifiers (business number, student id), detect when the same identifier appears elsewhere in the
document (e.g. inside a seal block or a second table) and surface that to the reviewer as
cross-corroboration. F-10 (`company_name` wrong) would then at least be shown alongside a correct
business number from the same document.
**Risk:** low. Purely additive reviewer guidance; never changes a value.

### P2-3 · Make evidence fields earn their place — LOW
`detection_confidence`, `polygon` and `transform` are persisted and never consumed; `OCRLine.
orientation_degrees` is never set; `results._evidence_from_dict` is lossy. Either consume them (seal
quality, orientation-aware evidence) or remove them. Also consider consolidating the duplicated
`validate_effective_document` computation on the document read path.

---

## P3 — future capabilities

- **CLOVA OCR Korean business-registration specialised model** as a *proposal* source feeding the
  existing gate — only if local extraction for that type must improve and the privacy constraint is
  formally relaxed. Korean-first, KR data residency, purpose-built.
- **Seal recognition** (`use_seal_recognition`) — directly addresses the stamp artefacts that break
  row grouping (F-08).
- **Optional VLM proposal generator** — output enters the existing `REVIEW_REQUIRED` gate with explicit
  low-trust provenance, is never authoritative, and is never compared as if it were. Only after P2-1.
- **Surya/docTR spike** as a second opinion on table structure, evaluated against the same corpus.

---

## Explicitly NOT recommended

| Do not | Why |
|---|---|
| Relax `MIN_STRONG_SIGNAL_WEIGHT`, `AMBIGUITY_MARGIN`, or the confirmation gate to "improve" metrics | These are what produced 0 false READY and 0 hallucinated fields. Any metric gain would be bought with the safety property. |
| Add an LLM/VLM as the authoritative extractor | The measured failure is structure plus an 88 %-line-level recogniser. A semantic model inherits the glyph error and discards determinism — the product's differentiator. |
| Adopt PP-OCRv6 | Korean is not in its language set. The "+5.1 % over v5" headline is not a Korean gain. |
| Rewrite the verification engine or the evidence model | They are correct. Zero false READY across 8 scenarios, truthful evidence, correct null semantics. |
| Adopt PP-OCR-VL / PP-ChatOCRv4 as the primary path | Better page-level parsing, *worse* fine-grained geometry than PP-StructureV3, and a GPU-oriented serving story. |
| Do global deskew / denoise / binarisation | The prior round measured real-document skew far below the helpful threshold. Global application without evidence is a regression waiting to happen. |
| Report aggregate accuracy without listing wrong non-null values | The 3 wrong values (one at 0.9955) are the most important result in this evaluation. |