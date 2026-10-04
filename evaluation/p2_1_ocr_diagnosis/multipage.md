# Multipage Validation

**Verdict: PASS**, with one metric that cannot be measured and is recorded as
BLOCKED rather than assumed.

All seven frozen documents are single-page, so multipage behaviour was
previously untested. P2 recorded a multipage probe that stalled and reported
nothing. This phase ran it to completion.

## Method

Multi-page PDFs were built by repeating one real page from the private corpus
1, 3 and 6 times, then pushed through the **production upload and process
path** — real HTTP, real PaddleOCR, real validation, real verification. The
private original was opened read-only and the synthetic copies were written to
a temporary directory outside the repository.

## Results

| Pages | Upload | Process | ms/page | Terminal status | Fields | Non-null | Error |
|---|---|---|---|---|---|---|---|
| 1 | 201 | 21 239 ms | 21 239.9 | COMPLETED | 4 | 1 | none |
| 3 | 201 | 43 544 ms | 14 514.9 | COMPLETED | 4 | 1 | none |
| 6 | 201 | 86 181 ms | 14 363.6 | COMPLETED | 4 | 1 | none |

## Reading these numbers

**Cost is linear in page count.** 3× the pages costs 2.05× the time, 6× costs
4.06×. There is no super-linear blow-up at 6 pages, which is the failure mode
that matters for the pixel and time budgets.

**Per-page cost *drops* with more pages** (21.2 s → 14.4 s). That is engine
warm-up, not a speed-up from batching: the first page of the first document
pays one-time model initialisation. ADVS submits one page per OCR worker call
and does not batch, so the marginal per-page cost is the honest figure and the
1-page number is inflated by warm-up.

**Field output is identical at 1, 3 and 6 pages** — 4 fields, 1 non-null, no
errors. Repeating a page produced no duplicated fields, no double-counted
values and no cross-page contamination. This is the specific risk multipage
introduces, and it did not materialise: row grouping is page-scoped and the
issuance-date inference refuses to look past a page boundary.

**No resource limit was hit.** The configured ceilings are 30 pages,
25 000 000 pixels per image and 250 000 000 total render pixels. Six pages of
this document sit far below all three.

## BLOCKED: queue wait

**Queue wait cannot be measured, because there is no queue.** Document
processing runs inline inside the request handler
(`POST /documents/{id}/process` awaits the whole pipeline). There is no
background worker, no task queue and no scheduler in this codebase.

This is a fact about the architecture, not a gap in the test. It also means:

- A slow document holds an HTTP request open for its full duration. The 6-page
  case held a request open for 86 seconds.
- There is no queue-depth or back-pressure signal to measure.
- Concurrency is bounded only by the number of in-flight requests.

If per-request latency matters for real use, that is a design question for a
later phase, not something this validation can settle.

## Limits of this result

- Pages are **repeats of one document**, so they are near-identical. Real
  multipage input with differing content per page is not covered.
- The 30-page configured maximum was not exercised. Six pages is 20% of it.
- Memory was not instrumented. Only wall-clock time was measured.
- `max_pdf_render_pixels` is cumulative across pages, so the worst case is a
  30-page document of the largest page size, which is untested here.
