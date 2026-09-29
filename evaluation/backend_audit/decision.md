# Decision record

Written **after** audit + research + baseline + experiments, and **before** the
production changes were finalised. Each change is tied to a measured failure.

---

## 1. Actual dominant failure categories

Measured on the one authorised real document plus constructed controls:

| Rank | Category | Count | Impact |
|---|---|---|---|
| 1 | `LAYOUT_LOSS` | 3 | caused the total failure (UNKNOWN + all fields lost) and a confidently wrong value |
| 2 | `PDF_ROUTING` | 1 | silently dropped an entire scanned page |
| 3 | `FIELD_CANDIDATE_RANKING` | 1 | returned the secondary major instead of the primary |
| 4 | `EVIDENCE_ASSOCIATION` | 1 | fabricated a value with two-page evidence |
| 5 | `ORIENTATION` | 1 | rotation unsupported (partially improved) |
| — | `OCR_RECOGNITION` | **0** | **the OCR model was not the problem** |

## 2. Assumptions in the current architecture that were wrong

1. **"OCR text is the product."** Recognition was essentially correct (0.90–1.00
   line confidence on every meaningful row), but the representation the
   extractor consumed had already discarded the structure it needed.
2. **"A text line is the unit of layout."** A letter-spaced label is several
   detected boxes. Collapsing them into one string made `성명` and `전공`
   non-existent as substrings.
3. **"Embedded text is a document-level property."** It is a page-level one.
4. **"First match is the match."** With no scoring, the first *valid* candidate
   is not necessarily the right one.
5. **"A high OCR confidence implies a trustworthy value."** A footnote fragment
   scored 0.908 and passed the 0.90 trust floor.
6. **"A filename is harmless metadata."** It was in the classifier's haystack.
7. **"Preprocessing is wired up."** `ImagePreprocessor` has no callers.

## 3. What was already working well — and is retained unchanged

- `normalize_*` returning `None` rather than guessing. Correct throughout.
- Deterministic verification (`engine.py`, `submission.py`). **Untouched.**
- Raw-vs-normalized separation, evidence provenance, human review, effective
  field resolution, status semantics, workflow architecture.
- The abstention principle itself — the instinct was right, the implementation
  of *what counts as a candidate* was not.
- `canonical result` / provider-independent `OCRDocumentResult`.
- The classifier's weighted-signal design; only its **input** was wrong.

## 4. What should remain unchanged

Verification, persistence, workflow, status semantics, review workflow,
contracts, the mock provider, `EvidenceSufficiencyPolicy` v1.

## 5. What should be refactored

`extraction/base.py` — unify the text and geometry paths behind one
row-based candidate engine (done). `services/processing.py` — per-page routing
(done).

## 6. What should be replaced

Nothing was replaced wholesale. Providers are unchanged; the pipeline is
unchanged; only *parameters and candidate selection* changed.

## 7. What should NOT be added

- No LLM/VLM on the pipeline. See `research_review.md` §4.
- No cloud OCR. Privacy decision not made by the owner.
- No table model yet — no evidence yet that it is needed on this corpus.
- No fuzzy label matching. Measured false-match risk not established as
  acceptable.
- No business-number checksum (none could be authoritatively confirmed).
- No Phase 9 / admin panel.
- No `ImagePreprocessor` wiring — it would be speculative; deleting it is
  tracked as a cleanup, not done here.

## 8. Chosen architecture

**Architecture B — improved rasterization + layout-preserving representation +
shape-validated candidate ranking, with deterministic verification intact.**

Not chosen: C (cloud — privacy decision not made, uncalibrated confidence, 1 TPS),
D (semantic fallback — no evidence of need once layout is preserved),
E (VLM-first — non-deterministic, privacy, unverifiable Korean numbers).

## 9. Evidence supporting the decision

- **E1**: 144 → 288 DPI recovers the title, 36 → 32 boxes, conf 0.911 → 0.933,
  no latency cost.
- **E2**: always-on orientation **regressed** upright documents (0.933 → 0.717);
  a conditional retry is the only evidence-supported form.
- **E3**: real document `student_name` None → correct, `department` wrong →
  correct, `university_name` confidently wrong → safe abstention, with
  **zero** change on 137 synthetic samples and **False READY still 0**.
- **E4**: mixed PDF page 2 contributed 0 characters before; now OCR'd.
- **E5**: cross-page fabricated value eliminated.
- **E6**: filename removed from classification.

**Ablation is the strongest single piece of evidence**: the synthetic dev and
held-out splits are *bit-for-bit identical* before and after
(95.24/83.75/48.84/96.51/0 and 90.62/82.84/46.15/96.15/0). This works only
because the text path was re-expressed as single-segment rows so the benchmark
exercises the **new** algorithm rather than a legacy one.

## 10. Honest limits of this decision

The evidence rests on **one real document**. It proves the specific failure
modes measured and shows no regression anywhere else. It does **not** establish
general real-world reliability, and no claim to that effect should be made. Six
of eight supported document types have never been tested against a real
document. Broader validation requires a real corpus, which the project does not
yet have.
