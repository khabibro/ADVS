# Frozen Baseline

These are the historical P2 numbers, recorded verbatim. **Nothing here was
recomputed, rounded differently, or replaced.** P2.1 is a diagnosis phase; the
baseline is a fixed reference point, not a result.

## Historical P2 baseline (frozen, not modified)

| Metric | Frozen value |
|---|---|
| Field recall | **0.4706** |
| Wrong non-null values | **1** |
| False READY | **0 / 7** |
| Processed documents | **7 / 7** |
| Classification correct | **7 / 7** |
| Documents requiring review | **7 / 7** |
| OCR rendering baseline | 288 DPI nominal |
| Correct fields (frozen gold v1) | 16 |
| Unresolved (frozen gold v1) | 17 |
| Not evaluated (frozen gold v1) | 7 |

The frozen scorer (`evaluation/backend_round2/run_round2.py`, SHA-256
`de667f011d196c8cdbc292bd2a198a82d7b752c899957492fb165b9a15db8f64`) and the
frozen gold were **not edited**. A versioned semantic gold v2 exists in
gitignored runtime storage from P1/P2; it is read here but was not modified
either.

## Reproduced runtime configuration

Confirmed by direct probe of the running adapter and settings, not copied from
the previous report:

| Item | Measured value |
|---|---|
| Branch | `main` |
| HEAD | `48e3824a780e3c051cba2d2eb1838851db1fcf1e` (unchanged start to finish) |
| Python | 3.12.14 (`apps/api/.venv312`) |
| PaddlePaddle | 3.1.1 |
| PaddleOCR | 3.2.0 |
| Device | CPU |
| Language | `korean` |
| Detector | `PP-OCRv5_mobile_det` |
| Recognizer | `korean_PP-OCRv5_mobile_rec` |
| Configured render DPI | 288 |
| Document orientation classifier | enabled, conditional retry only |
| Textline orientation | disabled |
| OCR worker timeout | 120 s |
| Max PDF pages | 30 |
| Max upload | 20 MB |
| Max image dimension / pixels | 16 000 px / 25 000 000 |
| Max total PDF render pixels | 250 000 000 |
| Max OCR temp bytes | 100 000 000 |
| Total OCR observations captured | **650** |

650 observations matches the count P2 reported, which confirms the capture is
the same production path rather than a different configuration.

## An instrumentation defect found while recording this

**Page metadata reports `render_dpi: 288` for every page, but one document is
not rendered at 288 DPI.** `PaddleOCRProvider._normalize_page` sets
`render_dpi` from `self.render_scale`, which is the *configured* DPI. The
actual per-page scale is decided later, per page, by `_page_render_scale`, and
is recorded correctly only inside `metadata["transform"]`.

Measured, per document:

| Safe ID | Source | Effective render scale | Effective DPI | Reason |
|---|---|---|---|---|
| REAL-001 | PDF, 1117×1408 pt box | **1.5** | **108** | `source_resolution_fit` |
| REAL-004 | PDF, 595×842 pt | 4.0 | 288 | `configured_render_dpi` |
| REAL-005 | PDF, 595×842 pt | 4.0 | 288 | `configured_render_dpi` |
| REAL-002 | PNG, 595×842 px | n/a | native ~72 | raster, no resampling |
| REAL-003 | JPEG, 743×1020 px | n/a | native ~90 | raster, no resampling |
| REAL-006 | WEBP, 1200×1854 px | n/a | native | raster, no resampling |
| REAL-007 | JPEG, 400×566 px | n/a | native ~48 | raster, no resampling |

Consequences, stated plainly:

1. The corpus is **not** a uniform 288 DPI baseline. Four of seven documents
   reach the recognizer at their native raster resolution, which ranges from
   roughly 48 DPI to 200 DPI.
2. Any evidence record or provenance field that reads `render_dpi` from page
   metadata is **wrong for REAL-001**. The true value is in
   `metadata["transform"]["effective_render_dpi"]`.
3. The raster documents are never upsampled. REAL-007 reaches OCR at about
   48 DPI and REAL-002 at about 72 DPI.

This is a **provenance/observability defect**, not a measured cause of any
field failure in this phase — no failing field was traced to it. It is
reported because it means render-DPI reasoning from page metadata alone is
unsound, and because the "288 DPI baseline" framing in earlier reports is not
literally true of this corpus.

## Numeric OCR defaults are not pinned

ADVS sets no detector box threshold, no recognizer character threshold, no
batch size and no CPU thread count. Whatever PaddleOCR 3.2.0 defaults to is
what runs, and ADVS does not record those numbers. This remains a
reproducibility limitation and is unchanged from P2.
