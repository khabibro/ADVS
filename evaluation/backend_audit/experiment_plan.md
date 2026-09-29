# Experiment plan and results

All experiments ran locally. Real-document experiments used the single
authorised real document; no document was ever transmitted off the machine.
Synthetic controls were constructed to reproduce measured failure structures.

---

## E1 — Rasterization DPI

**Hypothesis.** 144 DPI (PaddleOCR's own default, which ADVS inherited) is too
low for small Hangul and for letter-spaced labels, and causes detector
fragmentation.

**Failure category targeted.** `RASTERIZATION` → `LAYOUT_LOSS`.

| Scale | DPI | Detected boxes | Mean line conf | Labels recovered | Wall clock |
|---|---|---|---|---|---|
| 2.0 (**baseline**) | 144 | 36 | 0.9113 | 7/9 (`재학증명서` **missing**) | 11.1 s |
| 3.0 | 216 | 33 | 0.9184 | 8/9 | 8.4 s |
| 4.0 | **288** | **32** | **0.9325** | **8/9** | 8.9 s |

(The 9th label, `학번`, is genuinely absent from this 재학증명서 layout — an
absence, not a failure.)

**Result.** At 144 DPI the title was recognized as `재 / 학증 / 5명 / 서` — one
fragment misread — so `재학증명서` never existed as a contiguous substring and
the highest-weight classification signal was lost. 288 DPI fixes it, reduces
fragmentation, and raises confidence, at no measurable latency cost.

**Conclusion.** Adopted as `paddle_ocr_render_dpi` default 288, clamped to
[1.5, 6.0]× so an absurd setting cannot exhaust memory.

**Regression risk.** Higher DPI raises peak memory ~4× vs 144 DPI. Accepted:
A4 at 288 DPI is ~8.4 MP.

---

## E2 — Conditional vs always-on orientation correction

**Hypothesis.** PaddleOCR's `use_doc_orientation_classify` improves rotated
captures.

**Failure category targeted.** `ORIENTATION`.

| Config | Upright real doc | Rotated 90° copy |
|---|---|---|
| orientation **off** (old default) | 32 boxes, conf **0.933**, `ENROLLMENT_CERTIFICATE` | 58 boxes, 243 chars, `UNKNOWN` |
| orientation **always on** | 53 boxes, conf **0.717**, **`UNKNOWN`** ← regression | 37 boxes, 367 chars, `UNKNOWN` |

**Result.** Always-on orientation classification **regressed the common case**:
mean confidence fell 0.933 → 0.717 and the document re-broke to `UNKNOWN`. It
helped the rare case (243 → 367 chars) but did not recover the type either.

**Conclusion.** Adopted as a **conditional single retry**, triggered only when
the first pass looks orientation-damaged (mean line confidence < 0.80, or
< 120 recognized chars/page), keeping whichever pass scores higher on
confidence-weighted recognized characters. An earlier attempt during this audit
enabled it unconditionally and had to be reverted — this experiment is the
reason it is a retry.

**Regression risk.** A second inference pass costs ~2× latency, but only for
degraded pages. A retry failure is swallowed and the first pass is kept, so it
can never turn a usable result into an error.

---

## E3 — Layout-preserving rows + shape-validated candidate ranking

**Hypothesis.** The dominant failure is not recognition but loss of intra-row
structure; grouping detected boxes that share a baseline, and validating
candidates against field semantics, recovers the lost fields.

**Failure category targeted.** `LAYOUT_LOSS`, `FIELD_CANDIDATE_RANKING`,
`EVIDENCE_ASSOCIATION`.

**Treatment.** Row grouping (`ocr/layout.py`) + candidate generation and
ranking (`extraction/fields.py`), with the plain-text path re-expressed as
single-segment rows so both paths share one implementation.

**Result on the real document (288 DPI):**

| Field | Before | After | Verdict |
|---|---|---|---|
| `student_name` | `None` | correct | **recovered** |
| `department` | secondary major (**wrong**) | primary major | **fixed** |
| `university_name` | footnote garbage, conf 0.908, `SUFFICIENT` | `None` / review | **safe abstention** |
| `student_id`, `issue_date` | `None` | `None` | correct (absent from this layout) |

32 detected boxes → 17 rows; `성 명:…`, `전 공:…`, `입 학 일 자 :…` became
matchable again.

**Conclusion.** Adopted.

**Ablation.** Synthetic dev split: classification 95.24 %, extraction 83.75 %,
document-level 48.84 %, validation 96.51 %, **False READY 0** — *identical before
and after*. Held-out likewise unchanged (90.62 / 82.84 / 46.15 / 96.15 / 0).
Recreated-from-reference: 100 / 90.91 / 40.00 / 100 / **0**.

The text path was re-expressed rather than duplicated specifically so the
synthetic benchmark exercises the *new* algorithm; unchanged scores are
therefore meaningful non-regression evidence, not a stale measurement.

**Regression risk.** Two real defects were found and fixed by new tests during
this work: duplicate evidence entries when a value shared the label's last box,
and geometry-less lines being relocated to the end of a page (which broke
label-above-value pairing when only one line carried geometry).

---

## E4 — Page-level PDF routing

**Hypothesis.** The document-level "is there meaningful text?" gate is wrong for
mixed PDFs.

**Control.** 2-page PDF: page 1 with a 91-character digital text layer, page 2
a real scan.

| | Before | After |
|---|---|---|
| Routing decision | `EMBEDDED_TEXT` (whole document) | per page |
| Page 2 contributed | **0 characters** | OCR'd |
| Page 2 fields | **all lost, silently** | extracted |

**Result.** Confirmed. The single gate meant one good page suppressed OCR for
every other page, with no error, no warning, and no review flag.

**Conclusion.** Adopted. A page is routed to OCR unless it has its own usable
text layer; each `OCRResult` row now records its own `provider`.

---

## E5 — Page-scoped observations

**Hypothesis.** The "value on the next line" fallback can pair a label on page 1
with a value on page 2.

**Control.** Page 1 = bare label `학번`; page 2 = `202312345`.

| | Before | After |
|---|---|---|
| Value | `202312345` populated | `null` |
| Evidence pages | `[1, 2]` | none |

**Result.** Confirmed bug. Note the same-row geometry path was already
page-guarded; only the flattened line path was not.

**Conclusion.** Adopted — rows are page-scoped by construction.

---

## E6 — Filename leakage

**Hypothesis.** The classifier used `original_filename` as evidence.

**Result.** Confirmed by source: `haystack = _squash(f"{filename}\n{text}")`.
A file named `사업자등록증.pdf` containing a transcript would have been
classified as a business registration certificate.

**Conclusion.** Filename removed from the haystack; the parameter is retained
for call-site compatibility and logged (length only). Test asserts that a
filename alone can never produce a supported type.

---

## Experiments deliberately NOT run

| Not run | Why |
|---|---|
| Live CLOVA / Azure / Google comparison | No credentials; owner did not explicitly authorize transmitting documents. Reported from official docs and marked not-live-benchmarked. |
| LLM/VLM extraction benchmark | Same. Would also have required putting a probabilistic model on a deterministic path. |
| PP-StructureV3 layout model | Promising but adds ~1.2 GB of models and a large latency cost for a benefit not yet demonstrated on our corpus. Deferred, not rejected. |
| Second local OCR engine | Only one real document is available; a second engine would produce one more data point, not a comparison. Requires more samples. |
| Tesseract/easyOCR swap | Disqualified on Korean accuracy evidence before any local benchmark was warranted. |
