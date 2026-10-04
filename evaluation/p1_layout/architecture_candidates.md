# Architecture candidates and selection

## The question measurement actually answered

Before comparing architectures it is worth stating what the corpus says the
problem is. Over the 17 fields P0 left unresolved:

| Label state in the OCR output | Fields |
|---|---:|
| Label string **absent** | **8** |
| Label string present | 8 |
| Correctly absent per gold | 1 |

For 8 of 17, the recogniser did not produce the label at all — `사업자동록번호`
for a registration number, `법인 영(단체영)` for a company name, `학성 번:` for a
student id, `소속` where the alias list expects `학과` or `전공`. **No structural
model can recover a string the recogniser never emitted.**

Of the 8 where the label is present, the dominant failure is `COLUMN_STRUCTURE`:
the detector emits a **single box** containing `평점평균:3.50/4.0백분율:85.00/100`,
so the two table cells are one string with no geometric boundary between them.
That is a *detection granularity* limit, not a layout limit.

These two facts dominate everything below.

## The three candidates

### Architecture A — current OCR plus improved geometry heuristics

The P0 pipeline. A one-dimensional row model: boxes sharing a baseline form a
row, rows are ordered left to right, labels are matched within a row. No columns,
no sections, no tables.

### Architecture B — generic row/column/table reconstruction from OCR geometry

What P1 built, in `app/document_intelligence/layout/`:

- **columns** — vertical bands inferred from wide intra-baseline gaps, with a
  gap-ratio and a minimum column width, both swept rather than fitted;
- **sections** — vertical blocks separated by large vertical gaps or explicit
  bracketed headings, so a repeated label can be scoped to its block;
- **headers** — heading rows paired with the value row beneath them by column
  alignment, which is the only way to associate across rows.

It adds no dependency, no model, no second pass over the pixels, and costs
microseconds. It also adds three structural candidate sources to
`extraction/structural.py`.

**Measured outcome: the structure is real and correct, and it changes no field
outcome.** Column banding is genuinely detected (5 to 16 bands per page),
semester headings are genuinely detected (`<<2024학년도 2학기>>`,
`<<2025학 년도1학기>>`), and a real summary table pairs
`총평점평균 → 3.90/4.0` with a 2-pixel alignment error. Recall and precision are
byte-identical to A.

Both candidate sources that appeared to promise recall were disabled after
measurement:

| Source | What it promised | What it produced | Verdict |
|---|---|---|---|
| `issuer_block_token` | recover an institution printed as a standalone token in a signature block | the issuing authority (`국세청`), an anti-forgery legend (`위·변조방지용`), and footer boilerplate (`및 www.ceripia`) | **disabled** |
| `section_scoped_value` | scope a repeated label to its owning block, so one section means unambiguous | `총`, `총 려니` as institution names; a department value while a second major in another section went unconsidered | **disabled** |

Both failed for the same underlying reason, which is worth stating because it is
the general lesson: **the cue that marks a signature block (`장` in `총장`) is
frequently absent from the OCR output**, so "short token matching a shape" is the
only test left, and on these documents a shape also matches a tax office, a
security legend and a URL. A shape test is not evidence of role.

### Architecture C — PaddleOCR structural pipeline

- **Layout detection: measured.** `LayoutDetection(model_name="PP-DocLayout-S")`
  initialised in 5.3 s (0.5 s cached) and ran at 0.09–0.17 s per page. It returns
  region boxes with labels: `table`, `text`, `doc_title`, `header`, `image`, and
  so on.
- **Table recognition: BLOCKED_ENVIRONMENT.**
  `TableRecognitionPipelineV2` requires the `paddlex[ocr]` extra, which is not
  installed. An isolated probe venv could not inherit the project
  interpreter's site-packages, so measuring it would have required reinstalling
  PaddlePaddle. Not done.
- **Documented Korean support: none**, for both layout and table models
  (`research_notes.md`).

## Comparison

| Candidate | Recall | Wrong non-null | False READY | Table capability | Latency | Memory | Dependency complexity | Evidence quality | Maintainability | Decision |
|---|---:|---:|---:|---|---|---|---|---|---|---|
| A current | 0.471 | 1 | 0 | none | baseline | baseline | none | unchanged | unchanged | reference |
| B geometry structure | 0.471 | 1 | 0 | columns, sections, header/value | +microseconds | negligible | none | unchanged on the authoritative path | +1 module, 18 tests | **selected, sources disabled** |
| C PP-StructureV3 (layout) | not applicable | — | — | region labels only | +0.09–0.17 s/page | +4.8 MB model | +`doc-parser` extra | unchanged | +large pipeline | rejected |
| C table recognition | **BLOCKED_ENVIRONMENT** | — | — | cells + HTML | unmeasured | ~1 GB models | +`paddlex[ocr]` | unchanged | +heavy | rejected |

## Selection

**Architecture B, with all candidate sources disabled.**

The reasoning, in the order the rules require:

1. **False READY must remain 0.** B keeps it at 0 and adds no path that can emit
   a value without evidence.
2. **Unsafe wrong non-null must not increase.** B adds none. The two sources that
   would have increased it were removed precisely because they did.
3. **Structural correctness.** B's derived structure is verifiably correct on the
   real pages: real column bands, real semester sections, a real summary-table
   pairing at 2-pixel alignment error.
4. **Recall.** B does not improve recall on this corpus. Stated plainly rather
   than dressed up.
5. **Generalisation.** B is geometry-only and threshold-swept, with adversarial
   tests that pin the constants as structural.
6. **C is rejected** because its table component cannot be measured here, has no
   documented Korean support, costs roughly 1 GB of models, and — decisively —
   addresses the *cell-boundary* half of the problem while leaving the
   *recognition* half, which measurement shows is the larger half, untouched.

The rule "if a simpler architecture achieves nearly the same useful improvement
as a much heavier model, prefer the simpler architecture" applies with full
force: B's useful improvement over A is **zero**, so the bar C must clear is the
entire improvement, which it cannot demonstrate on this corpus.

## What is shipped

`layout/` and `structural.py` are shipped as a **measured, tested, unwired**
structural layer. They are not on the authoritative extraction path. Shipping
them is justified as a capability with regression tests and an honest ablation
record; **not** shipping them as active candidate sources is the decision that
protects False READY and wrong-non-null.

## What would change this conclusion

- A corpus where label text is present and cells are separately boxed. Then B's
  header/value and column sources would have something to bind to.
- Documented Korean support for a table model, plus a measurable Korean accuracy
  figure. Then C deserves a real benchmark.
- A detector that emits per-cell boxes instead of one box per table row. That
  addresses the actual measured blocker for the transcript GPA.