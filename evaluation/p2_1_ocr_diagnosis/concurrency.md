# Concurrency Validation

**Verdict: PASS**, on a deliberately narrow scope. Stating the scope up front,
because a narrow pass is easy to over-read.

P2 recorded a concurrency probe that produced no output and therefore claimed
nothing. This phase ran one to completion.

## Method

Two different documents from the private corpus, in **two different projects**,
processed **simultaneously from two threads** against one application
instance, through the production upload and process path.

Both threads shared the application instance, the database session factory and
— critically — the single cached `PaddleOCR` engine, because the provider is a
module-level cache. That is the real risk being tested: concurrent use of one
recogniser. A test with one engine per thread would not have exercised it.

The two threads were released from a `threading.Barrier` so their work overlaps
rather than interleaving by luck.

## Results

| Metric | Value |
|---|---|
| Documents | 2 |
| Projects | 2 |
| Wall clock | 21 727 ms |
| Sum of individual durations | 36 419 ms |
| Genuine overlap observed | **yes** (21.7 s wall vs 36.4 s summed) |
| Both terminal `COMPLETED` | **yes** |
| Correct document type per document | **yes** (both, distinct) |
| Field counts | 4 and 7 — each matches its own single-document run |
| Non-null counts | 1 and 2 — each matches its own single-document run |
| Duplicate document rows | **none** (1 row per project) |
| Error codes | **none** |
| State corruption | **none observed** |

Both documents produced exactly the same field and value counts they produce
when processed alone. No cross-talk between the two projects.

The overlap figure is the substantive one: wall clock is 60% of the summed
durations, so the two pipelines really did run at the same time rather than
serialising. Concurrency did not deadlock, did not corrupt state, and did not
degrade either result.

## What this does NOT establish

- **Two workers is not a load test.** No claim about 10, 50 or 100 concurrent
  documents. Throughput was not measured; only that two overlapping pipelines
  both succeed.
- **One run, one machine, CPU only.** No repetition, so this is not a
  flake-resistant result. A race that appears once in fifty runs would very
  likely have been missed.
- **SQLite.** Concurrency correctness on SQLite says little about PostgreSQL,
  which is what `docker-compose.yml` actually runs. Row-level locking and
  `SELECT FOR UPDATE` behave differently. This is the most significant gap.
- **The application-level lock was not stressed.** `lock_project` serialises
  per project, and these were different projects, so the lock was never
  contended. Two documents in the **same** project — the realistic
  double-upload case — is untested.
- **No queue, so no queue metrics.** See `multipage.md`: processing is inline,
  so wait time is request latency and there is no queue to measure.
- **PaddleOCR internal thread-safety is only weakly probed.** The shared
  engine handled two overlapping calls without visible corruption, but
  PaddleOCR does not document itself as thread-safe, and two calls is weak
  evidence. This is a latent risk, not a cleared one.

## Recommendation

Treat concurrency as **passing for the case exercised** and **unverified
beyond it**. The specific things worth closing before relying on concurrent
processing are, in order:

1. Same-project contention on `lock_project` (double upload).
2. PostgreSQL rather than SQLite.
3. Repeated runs, to distinguish a real pass from a lucky one.
