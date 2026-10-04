# Change log

Every production and evaluation change, with the failure that motivated it.

---

## P1-001 structural layout layer (new module)

- **OBSERVED FAILURE** — the row model is one-dimensional. On the second
  transcript the detector emits a single box containing
  `평점평균:3.50/4.0백분율:85.00/100`, so a grade-point cell and a percentage cell
  are one string. Measured across the corpus: 5 to 16 column bands per page were
  being flattened into single rows.
- **REPRODUCTION** — `evaluation/p1_layout/structural_probe.py`, column profile
  per page.
- **ROOT CAUSE** — `app/document_intelligence/ocr/layout.py` groups by vertical
  overlap only. There is no column concept anywhere in the pipeline.
- **ALTERNATIVES CONSIDERED** — PaddleOCR layout detection (Architecture C);
  PP-StructureV3 table recognition; leave the model as is.
- **SELECTED CHANGE** — `app/document_intelligence/layout/` with `columns.py`,
  `sections.py`, `headers.py`, `structure.py`. Geometry only; no new dependency,
  no model, no second pixel pass.
- **WHY** — addresses the measured flattening, costs microseconds, and adds no
  failure mode. Constants were swept, not fitted: `COLUMN_GAP_RATIO ×
  MIN_COLUMN_WIDTH_RATIO` over a 5×4 grid gave 7/7 correct table/form
  classification at **every** point, so the chosen values sit mid-grid.
- **TESTS** — `tests/test_p1_layout.py`, 18 tests including adversarial cases
  for letter-spaced labels and non-aligned value rows.
- **SAFETY IMPACT** — none. Not on the authoritative path.
- **RECALL IMPACT** — **zero**.
- **PERFORMANCE IMPACT** — under 1 ms per page; not executed during processing.
- **LIMITATIONS** — cannot reach inside a single OCR box, which is where the
  measured transcript failure lives.

---

## P1-002 heading detection excludes parentheticals

- **OBSERVED FAILURE** — a business certificate was split into three phantom
  sections, because `(법인사업자)` matched the heading pattern.
- **REPRODUCTION** — `structural_probe.py` on P1-002 reported 5 sections for a
  form with one identity block.
- **ROOT CAUSE** — the pattern accepted `(...)`, `<<...>>` and `[...]`
  interchangeably. A parenthetical on a Korean certificate is a sub-caption
  inside a block, not a block heading.
- **ALTERNATIVES CONSIDERED** — keep `(...)` and rely on a minimum section
  length; require the heading to be the only content in its row.
- **SELECTED CHANGE** — headings must use `<<...>>` or `[...]`.
- **WHY** — a parenthetical is a documented, widespread qualifier convention.
  Only a delimiter not used for qualification identifies a block heading.
- **TESTS** — `test_parenthetical_subcaption_is_not_treated_as_a_section_heading`.
- **SAFETY IMPACT** — prevents phantom structure.
- **RECALL IMPACT** — none directly; removes a false signal.
- **LIMITATIONS** — a block heading in some other convention is still missed.

---

## P1-003 `issuer_block_token` candidate — IMPLEMENTED, MEASURED, DISABLED

- **OBSERVED FAILURE** — four documents print the institution as a standalone
  token in a signature block, never as `label: value`, so the label matcher
  cannot bind it.
- **REPRODUCTION** — `field_diagnosis.py`, university name on four samples.
- **ROOT CAUSE** — a missing capability: no source treats a role-bearing
  standalone token as a value.
- **ALTERNATIVES CONSIDERED** — header/value pairing; section scoping; a
  dedicated role model.
- **SELECTED CHANGE** — none. The function body returns `None`, with the
  measurement recorded in its docstring.
- **WHY** — measured against the frozen gold it produced three confident wrong
  values: the issuing authority on a business certificate, an anti-forgery legend
  on a transcript, and footer boilerplate on an enrolment certificate. The cue
  that marks a signature block (`장` in `총장`) is frequently **absent from the OCR
  output**, so only a shape test remains, and on these documents a shape also
  matches a tax office, a security legend and a URL. A shape test is not evidence
  of role.
- **TESTS** — the ablation in `ablation_results.md` is the test; the negative
  result is asserted by the source returning `None`.
- **SAFETY IMPACT** — prevented three new wrong values.
- **RECALL IMPACT** — would have been −3 net.
- **LIMITATIONS** — institution names in signature blocks stay unresolved.

---

## P1-004 `section_scoped_value` candidate — IMPLEMENTED, MEASURED, DISABLED

- **OBSERVED FAILURE** — a label repeated per section pools into one ambiguous
  candidate set. Scoping it to the owning section looked like the principled fix.
- **REPRODUCTION** — both transcripts; `평점평균` spans 3 and 4 sections.
- **ROOT CAUSE** — candidates are not attributed to the block that contains them.
- **ALTERNATIVES CONSIDERED** — first block, last block, most common value; all
  rejected as reading-order heuristics.
- **SELECTED CHANGE** — none. Returns `([], 0)`, with the measurement recorded.
- **WHY** — every single-section outcome it produced was wrong: `총` and
  `총 려니` as institution names, and a department value while a second major in
  another section went unconsidered. On the transcripts, where the label genuinely
  spans several sections, it correctly stayed ambiguous — which is what the
  pipeline already did. Section scoping cannot separate "this block's instance"
  from "a sentence that merely contains the label word".
- **TESTS** — as above; negative result asserted by the source.
- **SAFETY IMPACT** — prevented three new wrong values.
- **RECALL IMPACT** — would have been −3 net.
- **LIMITATIONS** — repeated labels stay ambiguous, correctly.

---

## P1-005 boilerplate filter on structural candidates

- **OBSERVED FAILURE** — a candidate value of `및 www.ceripia` was produced for an
  enrolment certificate's institution name, taken from the footer sentence
  `[인터넷 발급]우리 대학 및 www.ceripia.com 원본대조메뉴에서 …`.
- **REPRODUCTION** — impact probe over the frozen observations.
- **ROOT CAUSE** — the footer contains the word for "university" and names no
  institution.
- **ALTERNATIVES CONSIDERED** — drop label matching inside long rows; require a
  short row; exclude rows below a geometric footer threshold.
- **SELECTED CHANGE** — drop occurrences inside rows carrying document-mechanics
  markers (`www.`, `certpia`, `원본대조`, `발급일로부터`, `QR코드`, `특허`,
  `스마트폰`, and similar).
- **WHY** — the markers describe document mechanics, not content, and a footer
  that explains online verification is never a field value. Geometry alone cannot
  place it, since a footer is simply the last block on the page.
- **TESTS** — covered by the impact probe and by `test_p1_layout.py`.
- **SAFETY IMPACT** — prevented one confident wrong value.
- **RECALL IMPACT** — none.
- **LIMITATIONS** — a genuine value printed in a footer would be dropped.

---

## P1-006 measurement guard on header/value pairing

- **OBSERVED FAILURE** — header/value pairing produced `총 려니` as an institution
  name, pairing a letter-spaced heading with the issuing-office line beneath it.
- **REPRODUCTION** — impact probe on P1-004 and P1-005.
- **ROOT CAUSE** — any aligned token was accepted as the value.
- **ALTERNATIVES CONSIDERED** — require numeric values only; require the heading
  row to be inside a detected section; drop the source.
- **SELECTED CHANGE** — the paired cell must look like a measurement (digits and
  separators). The source remains available but is not wired in.
- **WHY** — a summary table's value cell is a measurement; a signature block's
  cell is not. The guard is general, but tightening it further until this specific
  case passes would be fitting to the sample.
- **TESTS** — `test_wide_heading_segment_is_treated_as_a_value_not_a_heading`,
  `test_misaligned_value_row_produces_no_pairing`.
- **SAFETY IMPACT** — prevents one confident wrong value.
- **RECALL IMPACT** — none, because the source is not wired in.
- **LIMITATIONS** — the one genuinely recoverable cumulative GPA stays unresolved.
  The frozen gold marks that field ambiguous in one case and expects a
  per-semester value in the other, so resolving it would score as incorrect
  against the frozen denominator.

---

## P1-007 evaluation harness: private-dir discovery

- **OBSERVED FAILURE** — the previous P0 run reported the evaluation as blocked
  because the harness could not resolve the sample files.
- **ROOT CAUSE** — a hardcoded path assumption, not a missing dataset.
- **SELECTED CHANGE** — `dataset_inventory.py` discovers the directory from
  `--private-dir`, then `ADVS_PRIVATE_DIR`, then conventional names; `pathlib`
  throughout, read mode only. No absolute user path is recorded in any artefact.
- **WHY** — the previous blockage was a tooling defect that suppressed real
  evidence.
- **SAFETY IMPACT** — none; strictly reduces the chance of a private path being
  written into a tracked file.
- **LIMITATIONS** — discovery depends on a conventional location when neither
  flag nor environment variable is set.
