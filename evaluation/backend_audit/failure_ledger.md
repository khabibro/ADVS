# Failure ledger — human-readable summary

Machine-readable form: `failure_ledger.json`. Contains **safe metadata only** —
hashed sample IDs, document types, boolean presence, categories. No names, no
business-registration numbers, no raw OCR text, no page images.

## How samples were obtained

| Sample | Source | Ground truth | Committed? |
|---|---|---|---|
| `a1f4c0e91d2b` | 1 real 재학증명서 (enrollment certificate), found locally, used with explicit owner authorisation, processed **locally only** | Document type + 2 field values transcribed by the owner | **No** — the PDF lives under `evaluation/datasets/real/`, which is gitignored |
| `synthetic-control-1..3` | Constructed probes reproducing a measured failure structure | Constructed | Yes (no personal data) |

**There is no real-document corpus.** One real document is a single data point
with no per-field ground truth for 3 of 5 fields. All real-document metrics
below are reported at document level and are explicitly *not* comparable to the
synthetic benchmark.

## Failure taxonomy by earliest responsible stage

| Earliest stage | Before | After | Note |
|---|---|---|---|
| `PDF_ROUTING` | 1 | **0** | document-level gate dropped an entire scanned page |
| `LAYOUT_LOSS` | 3 | **1** | remaining case is the signature-block university name |
| `FIELD_CANDIDATE_RANKING` | 1 | **0** | folded into `LAYOUT_LOSS` root cause |
| `EVIDENCE_ASSOCIATION` | 1 | **0** | cross-page label/value pairing |
| `ORIENTATION` | 1 | 1 | partially improved, not solved |
| `OCR_RECOGNITION` | 0 | 0 | **the OCR model was never the problem** |
| `NORMALIZATION` / `VERIFICATION` / `API` | 0 | 0 | |

## The central finding

On the real document, PaddleOCR read the meaningful content essentially
correctly — line confidences of 0.90–1.00 on every field row. Yet the pipeline
returned **zero** fields and the wrong document type.

Every failure traced back to a single root cause: **the detected text was
correct, but the representation the extractor consumed had already thrown away
the intra-row structure it needed.** A letter-spaced label (`성  명 :`) arrives
from the detector as 2–5 separate boxes; the extractor matched labels against
whole reconstructed lines, so `성명` never existed as a string.

Consequences cascaded from there:

1. The document title `재학증명서` was split into 5 boxes (one misread as `5명`),
   so the highest-weight classification signal never matched → `UNKNOWN`.
2. `UNKNOWN` disables the whole extractor registry → **all** fields lost.
3. Once type was recovered, the same fragmentation still cost `student_name`
   (label split) and returned the *secondary* major for `department` (the
   primary's label was split, the secondary's was not).

## Most important single finding (safety)

`university_name` was captured as:

```
및www.cer tpia.com 원본 대조 메뉴에서 증명서 하단의 인터넷
```

— a fragment of the document's verification footnote, triggered by the word
`대학` ("our university") inside it. Its OCR confidence was **0.908**, which is
**above** the 0.90 evidence-policy floor, so `EvidenceSufficiencyPolicy`
classified it `SUFFICIENT` with no review reason.

A confidently wrong value that passes the trust gate is more dangerous than an
explicit `null`, because verification and human reviewers both treat
`SUFFICIENT` as "no need to look at this". After the fix the same field is
`UNAVAILABLE`.

## What was NOT a cause

- **Not the OCR model.** At 288 DPI every meaningful row is read correctly.
- **Not normalization.** No normalization defect was observed on this sample.
- **Not verification.** Deterministic verification behaved correctly
  throughout; the damage was upstream of it, and unresolved fields correctly
  surfaced as review rather than as false deterministic failures.
- **Not the classifier's weighting.** The weights are reasonable; the problem
  was that its input string no longer contained the text it was matching on.
