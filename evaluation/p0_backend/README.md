# P0 backend stabilization artifacts

Sanitized P0 evidence and reports. These files deliberately exclude raw OCR text,
real document contents, names, identifiers, addresses, business numbers,
certificate numbers, ground-truth values and source filenames. Samples are
addressed only by stable internal ids (`DS-0xx`, `R2-0x`, `REAL-00x`).

## Status

The real-document evaluation is **no longer blocked**. The earlier blockage was
caused by the runner searching the Desktop root while the samples live in a
`samples` subfolder; the runner's path resolution was corrected and no source
file was moved or modified. `realistic_after.json` now records completed results
rather than a blocked status, and the denominator was not changed.

## Reading order

| File | Purpose |
|---|---|
| `final_report.md` | verdict, per-section findings, claim boundaries |
| `final_validation_start.md` | frozen starting state and evaluator hashes |
| `history_audit.md` | `721cc9d..f641fee` commit audit |
| `desktop_samples_inventory.json` | sanitized sample inventory |
| `desktop_samples_results.md` | current corpus results |
| `historical_comparison.md` | PRE-P0 vs POST-P0 on identical bytes |
| `live_http_smoke.md` | live HTTP end-to-end validation |
| `multipage_validation.md` | multi-page and timeout behaviour |
| `concurrency_validation.md` | F-13 concurrency behaviour |
| `review_closure.md` | F-16 review closure |
| `security_regression.md` | hostile uploads, F-01, F-17 |
| `quality_gates.md` | every gate command and result |

## Private material

Ground truth and raw machine output live in gitignored directories
(`evaluation/backend_round2/work/`, `evaluation/private_runtime/`) and are never
committed.
