# Concurrency validation (F-13)

## Distinct documents, live backend

Three distinct corpus documents were uploaded and processed simultaneously
against a running `uvicorn` server.

| Document | Upload | Processing result | Error code | Duration |
|---|---|---|---|---|
| 1 | 201 | COMPLETED | none | 12.6 s |
| 2 | 201 | COMPLETED | none | 25.5 s |
| 3 | 201 | COMPLETED | none | 19.2 s |

Wall clock 25.9 s against 57.3 s of summed duration, so the work genuinely
overlapped rather than serialising by accident of timing.

Verified:

- all three uploads accepted
- all three eventually reached `COMPLETED`
- **no request returned `OCR_BUSY`**
- no database corruption; each document persisted its own fields and evidence
- bounded OCR concurrency preserved: one native OCR slot, requests queued behind
  it, which is why completion times spread rather than all landing together

## Same document, concurrent process calls

Four concurrent `POST /documents/{id}/process` calls on a **single** document:

| Caller | HTTP | Observed status | Error code |
|---|---|---|---|
| 1 | 200 | COMPLETED | none |
| 2 | 200 | OCR_PROCESSING (in flight) | none |
| 3 | 200 | OCR_PROCESSING (in flight) | none |
| 4 | 200 | OCR_PROCESSING (in flight) | none |

After the in-flight run settled:

| Check | Result |
|---|---|
| Document converges to COMPLETED | yes |
| Extracted field set identical before and after | yes — 7 fields, unchanged |
| Duplicate rows after reprocessing | none |
| `processing_version` | advanced monotonically, 1 → 2 |
| Any terminal error code | none |
| Any `OCR_BUSY` | none |

One caller wins the claim through an atomic conditional status transition; the
others observe an active status and return the document's current state
unchanged. That is the intended idempotency guarantee — a double-click or a
retried request cannot start a second concurrent pipeline over the same document.
The in-flight status returned to the losing callers is the correct report of
state, not a failure, and none of them carried an error.

## Worker slot behaviour

The OCR worker exposes exactly one slot and **queues** callers rather than
refusing them. A caller that cannot get the slot waits for it. `OCR_BUSY` exists
only as a legacy error code and a docstring; nothing in the current code raises
it. This is the F-13 fix, confirmed against the real provider and against the
live server.

## Timeout interaction

A timeout stops the caller waiting but does not release the slot early; the slot
is released when the native OCR thread finishes. The consequence is that a
genuinely wedged OCR thread would hold the slot until it exits. Measured
behaviour after a forced timeout showed the slot available for the next document
immediately afterwards, so on CPU-sized inputs the thread does exit promptly.

## Verdict

F-13 holds. Contention produces waiting, never a terminal `OCR_BUSY`, and neither
distinct-document nor same-document concurrency corrupts state.