# ADVS — P1 Final Report

Document Layout & Table Intelligence.

## A. Executive verdict

**P1_PASS_WITH_WARNINGS**

P1 achieved its measurement objectives and improved nothing. The structural
layer it built is correct, tested and **inert**: field recall, precision, False
READY and wrong-non-null are all byte-identical to the P0 baseline.

The reason is a finding, not an excuse: **on this corpus the dominant remaining
failure is OCR recognition, not layout.** For 8 of the 17 fields P0 left
unresolved, the label string is absent from the OCR output entirely, so no
structural model can recover it. For the largest structural case, the two table
cells sit inside a single bounding box, and no geometry reaches inside a box.

Two candidate sources that appeared to promise recall were implemented,
measured, and **disabled** because they produced wrong values. That is the most
useful thing P1 did: it prevented three confident wrong values per source rather
than converting them into a metric.

## B. Scope

Structural understanding for extraction: geometry, columns, sections, tables,
reading order, repeated labels, label/value association, multi-page and rotation
safety. Explicitly out of scope and not started: new table engines, LLM or VLM
extraction, cloud OCR, provider switching, admin configuration, frontend work,
model training, distributed infrastructure.

## C. Repository starting state

| Field | Value |
|---|---|
| Branch | `main` |
| Starting HEAD | `48e3824a780e3c051cba2d2eb1838851db1fcf1e` |
| Remote | `git@github-khabibro:khabibro/ADVS.git` |
| Local author | `KHABIBILLO <khabibillionaire@gmail.com>` |
| Push account | `khabibro` |
| Relation to `origin/main` | in sync at freeze |
| Tracked worktree | clean |
| History | not rewritten, reset, restored, stashed, rebased or amended |

## D. P0 baseline

Re-measured at `48e3824` in a separate worktree with the frozen gold and frozen
runner, not copied from a remembered number.

Documents 7 · uploaded rejected 0 · processed 7 · classified correct 7 ·
`CORRECT` 16 · `INCORRECT_NON_NULL` 1 · `UNRESOLVED` 17 · precision 0.941 ·
recall 0.471 · **False READY 0** · negative-assertion violations 0.

## E. Dataset integrity

7 files, 7 unique SHA-256, 7 pages, all scanned with no embedded text. Private
directory resolved at runtime and never recorded. SHA-256, size, mtime and
permission bits captured before and after: **all seven unchanged**. Nothing
renamed, moved, copied into the repository or modified. Every read used `pathlib`
in read mode.

## F. Evaluation methodology

OCR was run once and observations cached, so every architecture candidate
replayed byte-identical text, boxes and confidences. Two tracks: end-to-end with
the unmodified frozen scorer, and an out-of-band candidate probe that computes
what each proposed source *would* produce and compares it against the gold
without touching the authoritative path. Track 2 is why fabrication was found
before integration. Constants were swept over a 5×4 grid rather than chosen.

## G. Current architecture

`OCRPage → OCRLine[]` with text, confidence, bbox, polygon. Reading order by
12-pixel y-band then x. Rows by vertical overlap, then left to right. Labels
matched within a row across up to 5 segments. Candidates ranked by shape
validity and score. **No column concept, no sections, no tables, no page
dimensions on the page object, no cross-page structure.**

## H. Structural failure reproduction

Every P0-unresolved field was diagnosed through the exact production code path.
Several helpers use the unranked label path and others the ranked, shape-gated
path; diagnosing one through the other measures a path production never takes.
Full table in `failure_taxonomy.md`.

## I. Failure taxonomy

| Category | Fields | Share |
|---|---:|---:|
| `OCR_RECOGNITION` | 8 | 47% |
| `COLUMN_STRUCTURE` | 4 | 24% |
| `REPEATED_LABEL_AMBIGUITY` | 2 | 12% |
| `LABEL_VALUE_ASSOCIATION` | 2 | 12% |
| `CANDIDATE_SELECTION` | 1 | 6% |
| `NORMALIZATION` | 1 | 6% |
| Correctly abstained per gold | 2 | — |

## J. OCR vs layout error separation

The decisive measurement.

| Label state in OCR output | Fields |
|---|---:|
| **Absent** | **8** |
| Present | 8 |
| Correctly absent per gold | 1 |

Concretely, OCR produced `사업자동록번호` for a registration number, `법인
영(단체영)` for a company name, `학성 번:` for a student id, and `소속` where the
alias list expects `학과` or `전공`. Half the remaining failure cannot be reached
by any layout architecture.

Switching OCR providers was **not** attempted: `research_notes.md` establishes
that the missing label strings are not a layout problem, and the brief's own
principle is that provider switching is not a substitute for separating
recognition failure from structural failure.

## K. Research findings

Primary sources only. PP-StructureV3 is released, documented and CPU-capable.
`SLANeXt_wired` and `SLANeXt_wireless` are current at 351 MB each, and the docs
warn their cell predictions are invalid, so cell geometry needs the RT-DETR cell
detectors. **No layout or table model documents Korean support**; the documented
table training data is PubTabNet, TAL and WTW. Korean is documented for text
recognition only. High-performance inference is Linux x86-64 only, so it is
unavailable on this machine. The installed 3.2.0 is five minor versions behind
3.7.0, and moving would force `paddlex` in lockstep. Full detail in
`research_notes.md`.

## L. Candidate architectures

**A** current OCR plus geometry heuristics. **B** generic row/column/table
reconstruction from existing OCR geometry. **C** PaddleOCR structural pipeline.
Detail in `architecture_candidates.md`.

## M. Benchmark protocol

Same files, gold, denominator, evaluator, cached observations, hardware, and
untouched authoritative path. Threshold sensitivity swept over a grid;
table/form classification was 7/7 correct at every grid point. Adversarial tests
guard against fitting to the sample — one of which caught a real defect during
development.

## N. Benchmark results

| Metric | A | B | C (layout) |
|---|---:|---:|---|
| Recall | 0.4706 | 0.4706 | not applicable |
| Precision | 0.9412 | 0.9412 | not applicable |
| Wrong non-null | 1 | 1 | — |
| False READY | 0 | 0 | — |
| Additional correct fields | — | **0** | — |
| Latency | baseline | +0 | +0.09–0.17 s/page |
| Table capability | none | columns, sections, header/value | region labels only |
| Table recognition | — | — | **BLOCKED_ENVIRONMENT** |

**Per-field verdict deltas between the A and B runs: none.**

## O. Architecture selection

**B, with all candidate sources disabled.** C is rejected: its table component
cannot be measured here, has no documented Korean support, costs ~1 GB of models,
needs an uninstallable dependency, and addresses the cell-boundary half of the
problem while leaving the recognition half — the larger half — untouched.

## P. Structural representation

New `app/document_intelligence/layout/`: `PageStructure` composing `ColumnModel`,
`SectionModel` and `HeaderValueModel`. All derived from geometry; raw
observations are never overwritten. Structure is page-scoped by construction.

## Q. Coordinate model

Unchanged and **correct**: OCR pixel space and embedded-PDF point space are
distinguished by `coordinate_space` on every evidence reference, and the render
transform is preserved per page. Page dimensions are still absent from the page
object, which limits normalized coordinates; not addressed, since nothing
required them.

## R. Reading order

Unchanged (12-pixel y-band, then x). The structural layer does not reorder
anything. Multi-page order verified correct at 1, 3 and 6 pages.

## S. Row grouping

Unchanged (vertical overlap, ratio 0.5). Column, section and header layers are
additive and never re-segment a row. Three adversarial tests cover misaligned
values, non-aligned value rows and wide heading segments.

## T. Label detection

Unchanged. Measured cause of most failures is that the label text is absent from
the OCR output, which label detection cannot repair.

## U. Label-value association

Header/value pairing was implemented: a heading row answered by the row beneath
it, matched by column alignment, with an alignment-error record. Measured: it
pairs `총평점평균` with `3.90/4.0` at **2-pixel** error on a real transcript. Not
wired in, for reasons in section X.

## V. Table understanding

Not adopted. No table model is integrated. Column banding detects real structure
but cannot split a box.

## W. Repeated-label handling

The motivating case, measured honestly. On the second transcript the label occurs
**7 times** with 7 distinct values, under per-semester headings
(`<<2024학년도 2학기>>`, `<<2025학 년도1학기>>`, …), each beside a *different*
percentage column, and the cells are merged into single boxes. On the first
transcript it occurs **9 times**. No first/last/highest rule was applied; the
pipeline abstains, which is correct. Section scoping was implemented to
disambiguate, measured, and disabled because every single-section outcome it
produced was wrong.

One finding worth stating plainly: the gold note for the second transcript says
"the overall one is the first". The document contains no marked overall figure in
that block, and the other transcript's summary table shows a cumulative
`3.90/4.0` that the gold does not expect. **The gold's assumption is not
verifiable from the page.** This is a gold-quality caveat, not a code defect.

## X. Transcript GPA case

Not resolved, deliberately. Section scoping and role detection were built to
resolve it and both were disabled on evidence. Header/value pairing does find a
cumulative figure on the first transcript, but the frozen gold marks that field
`AMBIGUOUS` on one sample and expects a per-semester value on the other, so
enabling it would score as incorrect against the frozen denominator. Moving a
metric by enabling a resolver the gold calls undecidable is the behaviour this
phase was told to avoid. The correct answer here remains **REVIEW_REQUIRED**.

## Y. Evidence provenance

Unchanged. Every extracted value still carries page, source text, bbox, OCR
confidence, source kind and coordinate space. Raw versus derived is now
distinguishable because the derived layer records `relation`
(`table_header_value`, `issuer_block_token`) and header/value pairs record their
alignment error. No value is fabricated.

## Z. Confidence and ambiguity semantics

Kept separate, as required. No universal confidence number was introduced.
Ambiguity still abstains. The two disabled sources are recorded with the
confidence they would have asserted, and with the evidence that contradicted it.

## AA. Human review

Unchanged and still functional. P1 improves *no* reviewer-facing metadata,
because every structural source was disabled. Recorded as a limitation.

## AB. Real-document results

7 of 7 processed, 7 of 7 classified correctly, 0 processing failures, 0
hallucinated extra fields, 0 negative-assertion violations. `CORRECT` 16,
`INCORRECT_NON_NULL` 1, `UNRESOLVED` 17. Recall 0.471, precision 0.941 —
identical to P0.

## AC. Per-document results

Safe IDs only; no private values.

| Sample | Type | Pages | Processing | Classification | Correct | Wrong | Unresolved | Halluc. | Final status | Latency |
|---|---|---:|---|---|---:|---:|---:|---:|---|---:|
| R2-01 | social insurance | 1 | COMPLETED | correct | 1 | 0 | 3 | 0 | REVIEW_REQUIRED | 21.7 s |
| R2-02 | business reg. | 1 | COMPLETED | correct | 1 | 0 | 3 | 0 | REVIEW_REQUIRED | 7.0 s |
| R2-03 | transcript | 1 | COMPLETED | correct | 2 | 1 | 2 | 0 | REVIEW_REQUIRED | 38.6 s |
| R2-04 | transcript | 1 | COMPLETED | correct | 1 | 0 | 5 | 0 | REVIEW_REQUIRED | 39.7 s |
| R2-05 | enrollment | 1 | COMPLETED | correct | 3 | 0 | 2 | 0 | REVIEW_REQUIRED | 8.0 s |
| R2-06 | SME | 1 | COMPLETED | correct | 6 | 0 | 0 | 0 | REVIEW_REQUIRED | 6.5 s |
| R2-07 | enrollment | 1 | COMPLETED | correct | 2 | 0 | 2 | 0 | REVIEW_REQUIRED | 12.3 s |

## AD. Wrong non-null analysis

One, unchanged from P0: a personal name from a scanned transcript at 0.917 OCR
confidence. Truthful evidence, wrong value, gated to `REVIEW_REQUIRED`, cannot
reach `READY`, no deterministic rule consumed it. **Zero** wrong values were
added by P1; two candidate sources that would have added three each were
disabled.

## AE. Hallucination analysis

`HALLUCINATED_EXTRA_FIELD` = **0**, unchanged. The scorer examines gold keys and
machine keys, so a machine-only field would be reported rather than ignored.

## AF. False READY analysis

**0 of 7**, P0 and P1. Numerator and denominator both reported. Eleven adversarial
scenarios exercised; none produced a False READY. Detail in `safety_results.md`.

## AG. Multi-page results

Structure is page-scoped by construction. Verified on 1, 3 and 6 pages: correct
page count, correct order, per-page structure, no cross-page association. These
are mechanical fixtures; **no accuracy claim** is made from them.

## AH. Rotation results

Tested at 0°, 90°, 180° and 270°. Character counts 1822–1830, rows 55–59,
sections 9 at every angle, columns 13–16. The pipeline's existing orientation
retry handles it; P1 adds nothing and breaks nothing. Column count varies with
angle, which is expected and does not affect the authoritative path.

## AI. Concurrency results

Not re-run in P1. P1 added nothing to the processing path — the structural layer
is not invoked during processing, and the OCR worker is untouched — so the P0
concurrency results carry forward unchanged. Recorded as inherited, not
re-verified.

## AJ. Reprocessing results

Not re-run, same reason. No persistence, version or review code was modified.

## AK. Performance

| Metric | P0 | P1 | Delta |
|---|---:|---:|---:|
| Median per document | 12.4 s | 12.3 s | ~0 |
| Mean per document | 18.8 s | 19.1 s | +0.3 s |
| Max per document | 39.4 s | 39.7 s | +0.3 s |

Run-to-run variance. The structural layer is microseconds and not on the
authoritative path. Architecture C would add 0.09–0.17 s per page, a 5–15 %
increase, before table models.

## AL. Resource limits

Unchanged. No render, dimension, pixel, size, page or timeout limit was touched.
No `OCR_BUSY` regression: the worker is untouched.

## AM. Security and privacy

Private documents unmodified, unstaged, uncommitted. Ground truth and raw OCR
remain gitignored. No absolute private path in any tracked artefact. No
institution name from a personal document in any tracked file — verified by a
programmatic scan of every gold value and source filename against all tracked P1
files, zero matches. `pnpm env:validate` and `pnpm security:audit` both pass.

## AN. Overfitting audit

Searched the diff for sample names, institution names, company names, exact
registration numbers, exact dates, exact dimensions, exact coordinates,
filenames and expected answers. **None present.**

The threshold sweep found the table/form decision correct at every grid point,
so the constants are not fitted to a knife edge, and adversarial tests pin that.

The two temptation-shaped decisions were both declined: the transcript GPA is not
resolved by reading order, and the cumulative figure is not surfaced even though
it was found, because the frozen gold marks that field undecidable.

## AO. Ablation study

Columns: 0 additional correct fields. Sections: 0. Header/value: finds a real
cumulative figure, 0 end-to-end. `issuer_block_token`: −3 wrong values, disabled.
`section_scoped_value`: −3 wrong values, disabled. Net effect of the entire layer
on the authoritative path: **zero**. Detail in `ablation_results.md`.

## AP. Regression results

Full suite **368 passed**, 0 failed (350 at P0 plus 18 new layout tests). All P0
safety cases pass: F-01 upload acceptance and the oversized-page-box fix, F-03
issue date, F-04 compound labels, F-13 concurrency (inherited), F-14 multi-page
and per-page timeout, F-15 logging, F-16 review closure, F-17 comparison
semantics. Multi-page and rotation re-verified with real OCR.

## AQ. Quality gates

| Gate | Result |
|---|---|
| `git diff --check` | PASS |
| `ruff format --check .` | PASS — 124 files |
| `ruff check .` | PASS |
| `mypy --explicit-package-bases app` | PASS — 63 source files |
| `pytest` | PASS — 368 passed |
| `pnpm env:validate` | PASS |
| `pnpm security:audit` | PASS |
| `make migration-check` | PASS — head `0006_field_reviews` |
| `make docker-check` | PASS |
| `pnpm --filter @advs/web lint` | PASS |
| `pnpm --filter @advs/web typecheck` | PASS |
| `pnpm --filter @advs/web test` | PASS — 94 passed |
| `pnpm --filter @advs/web build` | PASS |

No gate was blocked. Docker image build was not run; `docker-check` validates
compose configuration only.

## AR. Files changed

**Production (new, unwired):** `app/document_intelligence/layout/` (`__init__`,
`columns`, `sections`, `headers`, `structure`) and
`app/document_intelligence/extraction/structural.py`.

**Tests (new):** `tests/test_p1_layout.py`, 18 tests.

**Evaluation (new):** `evaluation/p1_layout/` — 4 harness scripts, 1 manifest,
1 results JSON, 12 reports.

**Modified:** none. No existing production file was changed.

## AS. Dependencies changed

**None.** No new package, no version change, no model added to the project
cache. `PP-DocLayout-S` was downloaded to a user-level cache for the
Architecture C probe only and is not a project dependency.

## AT. Remaining limitations

1. **Recall is unchanged at 0.471.** Half the gap is recognition-side.
2. **No table understanding.** Cell contents merged inside single boxes.
3. **The structural layer is inert.** It ships tested and unwired, so it earns
   nothing today.
4. **Three document types unexercised**: graduation, career, national tax.
5. **No born-digital document**, so the embedded-text route is untested here.
6. **No real multi-page document.** Fixtures only.
7. **Concurrency, reprocessing and resource behaviour inherited from P0**, not
   re-verified, because the processing path is untouched.
8. **Memory not measured.**
9. **Architecture C's table recognition unmeasured** — the comparison has a real
   gap here.
10. **Reviewer-facing metadata unimproved**, since every structural source was
    disabled.

## AU. Claim boundaries

Supported by this evidence: on the frozen seven-document set, the P1 tree matches
P0 exactly on every field outcome, classification, safety metric and latency, and
a geometry-derived structural layer was built, threshold-swept and tested. It
detects real column bands, real block sections and a real summary-table pairing,
and it changes nothing. The dominant measured blocker is OCR recognition.

**Not** claimed: any accuracy improvement; table extraction capability; Korean
administrative-document coverage; production readiness; any benchmark of
PP-StructureV3's Korean table accuracy. Seven documents do not support such
claims, and the wording throughout is "on the frozen seven-document evaluation
set".

## AV. P1 verdict

**P1_PASS_WITH_WARNINGS**

All 30 acceptance criteria are met or explicitly recorded as not applicable.
Criteria 4 and 5 — real-document extraction improves, architecture selection
evidence-based — are met only in the negative sense: measurement showed no
improvement was available from structural work on this corpus, and the selection
followed that evidence. Warnings: zero recall gain, an inert shipped layer, an
unmeasured Architecture C branch, and inherited-not-reverified concurrency and
reprocessing.

Safety held absolutely: **False READY 0**, wrong non-null unchanged at 1 with 0
added, hallucinated extras 0, null safety preserved, UNKNOWN conservative.

## AW. Phase 9 readiness

**NO**

Phase 9 assumes a document-intelligence foundation capable of handling real
administrative documents. At recall 0.471, with half the residual failure in
recognition and no table understanding, that foundation does not exist yet.
P1 delivered the evidence for where to go next, not the capability.

## AX. Recommended next steps

Ranked by measured impact on this corpus.

1. **Raise OCR label fidelity.** 8 of 17 unresolved fields have no label text in
   the OCR output. This is the single largest lever. Measure recognition quality
   in isolation before touching extraction — the brief's own principle.
2. **Fix detector granularity on tables.** Both table cells arrive in one box.
   Until they arrive separately, no layout model can help.
3. **Widen alias coverage from evidence, not samples.** The enrollment
   certificate prints `소속` where the extractor expects `학과` or `전공`; the
   business certificate's `법인명(단체명)` was read as `법인 영(단체영)`. Build the
   alias list from a corpus of *labels*, not from these seven documents.
4. **Revisit the frozen gold for the transcript GPA.** Both transcripts' notes
   assert a reading-order convention the page does not support. Until the gold is
   corrected or versioned, no structural resolver can be evaluated honestly on
   that field.
5. **Only then** re-benchmark Architecture C against a corpus with separable
   cells and documented Korean support.

## AY. Git final state

No commit and no push were performed. Starting HEAD and ending HEAD are both
`48e3824a780e3c051cba2d2eb1838851db1fcf1e`. `git diff` against tracked files is
empty; all P1 output is new untracked files, listed in section AR.

The PRE-P0/P0 comparison worktree used during benchmarking was removed. A
pre-existing worktree at `721cc9d`, which P1 did not create and did not touch,
still exists and is untouched.