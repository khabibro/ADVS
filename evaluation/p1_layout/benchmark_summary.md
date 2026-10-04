# Benchmark summary

Full comparison in `architecture_candidates.md`. Measured numbers here.

## End-to-end, frozen scorer

Both runs used the same 7 files, the same gold (`ff4b226c…`), the same unedited
runner and summariser, and the same cached OCR observations.

| Metric | A (P0 baseline) | B (geometry structure) | Delta |
|---|---:|---:|---:|
| Processed to completion | 7 | 7 | 0 |
| Classification correct | 7 | 7 | 0 |
| Fields `CORRECT` | 16 | 16 | 0 |
| Fields `INCORRECT_NON_NULL` | 1 | 1 | 0 |
| Fields `UNRESOLVED` | 17 | 17 | 0 |
| Fields `NOT_EVALUATED` | 7 | 7 | 0 |
| Field precision | 0.9412 | 0.9412 | 0 |
| Field recall | 0.4706 | 0.4706 | 0 |
| False READY | 0 | 0 | 0 |
| Negative-assertion violations | 0 | 0 | 0 |
| Median process time | 12.4 s | 12.3 s | ~0 |
| Mean process time | 18.8 s | 19.1 s | +0.3 s |
| Max process time | 39.4 s | 39.7 s | +0.3 s |

**Per-field verdict deltas between the two runs: none.** Every field on every
document resolved, abstained or failed identically. The mean-time difference is
run-to-run variance, not cost: the structural layer is not on the authoritative
path and is not executed during processing.

## Architecture C, layout detection

| Sample | Page size | Latency | Regions | Labels |
|---|---|---:|---:|---|
| P1-001 | 1676×2112 | 0.17 s | 2 | image, table |
| P1-002 | 595×842 | 0.09 s | 10 | image, text×6, doc_title×3, header_image, footer_image |
| P1-003 | 743×1020 | 0.10 s | 1 | table |
| P1-004 | 2381×3367 | 0.14 s | 1 | table |
| P1-005 | 2381×3367 | 0.14 s | 3 | image×2, text |
| P1-006 | 1200×1854 | 0.11 s | 4 | image, doc_title, header, header_image |
| P1-007 | 400×566 | 0.09 s | 9 | image, text×5, doc_title |

Init 5.3 s cold, 0.5 s cached; model 4.8 MB.

On both transcripts it returns a **single region labelled `table` covering the
whole page**. It therefore contributes a page-level "this is tabular" signal and
nothing finer. It does not bound cells, so it cannot address the measured
single-box contamination.

## Architecture C, table recognition

**BLOCKED_ENVIRONMENT.** `TableRecognitionPipelineV2` requires `paddlex[ocr]`,
which is not installed. Measuring it would have required reinstalling
PaddlePaddle in an isolated environment. Not attempted.

This is a genuine gap in the comparison. C's rejection does **not** rest on a
measurement of its Korean accuracy; it rests on documented absence of Korean
training data, ~1 GB of models, an uninstallable dependency, and the recognition-side
finding.

## What the benchmark establishes

1. The structural layer detects **real** structure: column bands, semester
   sections, and a summary-table header/value pairing at 2-pixel alignment error.
2. That structure changes **no** field outcome on this corpus.
3. The reason is measured, not assumed: 8 of 17 unresolved fields have no label
   text in the OCR output, and the largest structural case has both cells inside
   one bounding box.
4. Therefore a heavier structural stack, aimed at cell boundaries, would attack
   the smaller half of the problem while leaving the larger half untouched.
