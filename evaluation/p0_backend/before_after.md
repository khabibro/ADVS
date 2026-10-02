# Before / after

PRE-P0 is commit `721cc9d`, re-measured with the identical harness, gold and
scorer on the identical 7 files. Full detail in `historical_comparison.md`.

## Document metrics

| Metric | PRE-P0 | POST-P0 | Delta |
|---|---:|---:|---|
| Files in denominator | 7 | 7 | 0 |
| Upload rejected | 1 | 0 | -1 |
| Processed to completion | 6 | 7 | +1 |
| Pages processed | 3 | 7 | +4 |
| Classification correct | 3 | 7 | +4 |
| Classification accuracy | 0.500 | 1.000 | +0.500 |
| `UNKNOWN` classification | 3 | 0 | -3 |
| Fields `CORRECT` | 4 | 16 | +12 |
| Fields `INCORRECT` | 0 | 1 | +1 |
| Fields `UNRESOLVED` | 25 | 17 | -8 |
| Fields `NOT_EVALUATED` | 3 | 7 | +4 |
| Field precision | 1.000 | 0.941 | -0.059 |
| Field recall | 0.138 | 0.471 | +0.333 |
| **False READY** | **3** | **0** | **-3** |
| Negative-assertion violations | 0 | 0 | 0 |
| Null-derived mismatch | 0 | 0 | 0 |
| Null-derived expiry | 0 | 0 | 0 |

## Engineering metrics

| Metric | PRE-P0 | POST-P0 | Delta |
|---|---|---|---|
| Backend tests passing | 340 | 350 | +10 |
| Backend tests failing | 0 | 0 | 0 |
| Concurrent terminal `OCR_BUSY` | confirmed | none; callers queue | fixed |
| Multi-page timeout architecture | document-level ceiling | per-page | fixed |
| Extracted-but-unreviewable fields | present | 0 across all 8 types | fixed |
| Logging independence from root level | absent | present | fixed |
| Comparison whitespace handling | produced false mismatch | whitespace-insensitive | fixed |
| Legitimate large-page PDF at upload | rejected | accepted | fixed |
| Legitimate low-DPI large-page PDF at OCR | processed | processed (after fixing a P0 regression) | held |

## Reading the two regressions

Both are small and both are understood.

**Precision fell and one wrong value appeared.** A scanned transcript yields one
incorrect personal name at high OCR confidence. It is gated to
`REVIEW_REQUIRED` by the evidence policy and cannot reach `READY`, so it is not a
safety regression, but it is a genuine accuracy defect and the top item for the
next phase.

**`NOT_EVALUATED` rose from 3 to 7.** Four documents that previously produced no
field rows now emit complete field sets with unresolved values, because the
extractor registers expected fields even when it cannot fill them. The
denominator of evaluated fields rose with it (29 to 34). This is increased
visibility of missing values, not new extraction.
