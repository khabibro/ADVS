# Multi-page and timeout validation (F-14)

All results below come from the **real PaddleOCR provider on CPU**, not a mock.

## Multi-page processing

The Desktop corpus contains no multi-page document, so multi-page behaviour was
validated with mechanical fixtures: a real corpus page rendered into 1-, 3- and
6-page PDFs. These fixtures validate the **timeout, capacity, page-provenance
and ordering architecture only**. No extraction-accuracy claim is made from them,
and none is made below.

| Pages in | Pages out | Page numbers | Ordering | Chars per page | Render scale per page | Wall time |
|---|---|---|---|---|---|---|
| 1 | 1 | `[1]` | correct | 402 | 1.5 | 16.5 s |
| 3 | 3 | `[1, 2, 3]` | correct | 402 each | 1.5 each | 31.1 s |
| 6 | 6 | `[1, 2, 3, 4, 5, 6]` | correct | 402 each | 1.5 each | 64.0 s |

Checks passed:

- every page returned for 1, 3 and 6 pages
- page provenance correct and ordered on every page
- every page produced text; no page silently dropped
- render scale identical across pages of one document
- **no whole-document timeout ceiling**: 6 pages took 64.0 s against 16.5 s for
  one page. Processing time scales with page count, so a long document is not
  cut off by a single document-level deadline.

The render scale of 1.5 on these fixtures is the source-resolution fit described
in `final_report.md` section K: the fixture pages carry a raster whose own
resolution is below the configured render DPI, so the page renders at its
available resolution instead of being rejected.

## Per-page timeout semantics

Timeout is scoped **per page**, not per document. A page that exceeds the
timeout raises `OCR_TIMEOUT` naming that page.

Forced-timeout probe: a 3-page document processed with a 0.05 s per-page timeout
raised `OCR_TIMEOUT` as designed.

## Timeout recovery

Immediately after the forced timeout, on the same process and the same provider
instance:

| Probe | Result |
|---|---|
| 3-page document, normal timeout | 3 pages, 31.8 s |
| single-page document afterwards | 430 characters recognised |
| OCR slot released | yes — the next call ran to completion |

No stuck lock, no stuck semaphore, no permanent `OCR_BUSY`, no poisoned worker,
no corrupt document state. A timeout stops the caller from waiting; it does not
strand OCR capacity, because the slot is released when the native OCR thread
actually exits rather than when the caller gives up.

## Concurrent OCR on one provider

Three OCR calls issued concurrently on a single provider instance:

| Call | Pages | Chars | Duration |
|---|---|---|---|
| 1 | 1 | 430 | 4.6 s |
| 2 | 1 | 353 | 9.5 s |
| 3 | 1 | 430 | 14.0 s |

Wall clock 14.0 s against a summed 28.1 s of work. **No errors, no `OCR_BUSY`**,
all three returned text. Durations increase with submission order, which is the
expected signature of queued access to a single bounded slot rather than
unbounded parallel OCR.

## Scope of these claims

These results establish that multi-page documents are not subject to a
whole-document timeout ceiling, that page provenance and ordering survive, and
that a timeout does not poison OCR capacity. They do **not** establish extraction
accuracy on multi-page documents, because no real multi-page administrative
document was available.