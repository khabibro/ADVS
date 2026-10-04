# Performance results

## Authoritative path, P0 baseline vs P1 tree

Same machine, CPU only, same OCR model cache.

| Metric | P0 baseline | P1 tree | Delta |
|---|---:|---:|---:|
| Documents processed | 7 | 7 | 0 |
| Total processing time | 131.8 s | 133.8 s | +2.1 s |
| Median per document | 12.4 s | 12.3 s | ~0 |
| Mean per document | 18.8 s | 19.1 s | +0.3 s |
| Max per document | 39.4 s | 39.7 s | +0.3 s |
| Time per page | 18.8 s | 19.1 s | +0.3 s |

The difference is run-to-run variance. **The structural layer is not on the
authoritative path and adds no per-document cost.** It is microseconds of pure
geometry when invoked directly, and it is not invoked during processing.

## Structural layer cost, measured directly

| Operation | Cost |
|---|---|
| `build_page_structure`, 56-row page | well under 1 ms |
| Columns over 7 documents | < 1 ms total |
| Sections over 7 documents | < 1 ms total |
| Header/value detection over 7 documents | < 1 ms total |

## Architecture C cost, measured

| Operation | Cost |
|---|---|
| `PP-DocLayout-S` init, cold | 5.3 s |
| `PP-DocLayout-S` init, cached | 0.5 s |
| Layout detection per page | 0.09–0.17 s |
| Model size | 4.8 MB |
| Table recognition | unmeasured, BLOCKED_ENVIRONMENT |
| Full PP-StructureV3 default set | ~1.8 GB of models |

Adding Architecture C to a 12–40 s per-document CPU budget would cost roughly
1–2 s per page, a 5–15 % increase, before any table model cost.

## Memory

**Not measured.** Peak RSS was not captured for any candidate. This is a gap.

The structural layer's memory is bounded by the observation objects it already
references, so it adds no allocation beyond the derived structures. Architecture
C's memory footprint is unquantified here.

## Multi-page and orientation

Not measured in P1. The structural layer is page-scoped by construction —
`PageStructure` is built per page and no structure spans pages — but no
multi-page document or rotated capture was available to exercise it. Recorded as
untested, not as passing.
