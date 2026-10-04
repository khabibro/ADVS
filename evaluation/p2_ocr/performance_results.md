# Performance Results

## OCR adapter capture

Fresh current-stack OCR: seven documents, seven pages, median measured page
duration 12.716 seconds, maximum 39.331 seconds. Per-page OCR durations are not
the same as full workflow processing latency.

## Production workflow

The production HTTP path processed all seven one-page documents and reprocessed
each one. First-process median was 12.275 s, maximum 39.903 s, and total first
process time was 128.632 s. The end-to-end harness, including reprocessing,
took 256.4 s. All read-backs were stable and all reprocesses preserved field-row
counts and field outputs.

## Multi-page and concurrency

A local real-provider probe attempted two distinct documents concurrently,
then 1/3/6-page PDFs. It reached the first multipage (1-page) call but was
interrupted after it did not return within the probe window. Since the probe
prints only after all calls finish, no per-call result can be independently
reported; concurrency completion is likewise inconclusive. It is not an
authoritative API workflow test.

No memory measurement, queue-wait distribution, completed 1/3/6-page latency,
or verified concurrent-document result is claimed.
