# P1 — Document Layout & Table Intelligence

Sanitized P1 evidence. No names, identifiers, addresses, registration numbers,
institution names from personal documents, ground-truth values or raw OCR text
appear in any tracked file here.

## Headline

P1 measured the structural failures on the frozen seven-document corpus,
benchmarked three architectures, and **found that the structural layer it built
resolves nothing on this corpus**. Every proposed structural candidate source was
implemented, measured against the frozen gold, and disabled when it produced
wrong values. The authoritative extraction path is unchanged.

The measured reason is that **the dominant failure on this corpus is OCR
recognition, not layout**: for 8 of the 17 unresolved fields the label text is
absent from the OCR output entirely, so no geometry can recover it.

## Reading order

| File | Contents |
|---|---|
| `final_report.md` | full report, sections A–AY |
| `baseline_state.md` | frozen P0 baseline and environment |
| `dataset_manifest.json` | sanitized inventory with hashes and geometry |
| `failure_taxonomy.md` | per-field root cause, ranked by measured frequency |
| `architecture_candidates.md` | the three candidates and what each assumes |
| `research_notes.md` | primary-source findings, separated from inference |
| `benchmark_protocol.md` | how candidates were compared fairly |
| `benchmark_results.json` | raw measurements |
| `benchmark_summary.md` | architecture comparison and selection |
| `ablation_results.md` | what each component contributed |
| `performance_results.md` | latency and cost |
| `safety_results.md` | False READY, wrong non-null, null safety |
| `changes.md` | every change with observed failure and rationale |

## Harness

| Script | Purpose |
|---|---|
| `dataset_inventory.py` | private-dir discovery (never hardcoded), hashes, geometry |
| `observation_cache.py` | capture OCR once, replay identical observations to every candidate |
| `structural_probe.py` | row/column/section structure per page, per document |
| `field_diagnosis.py` | per-field diagnosis against the exact production code path |

The private document directory is discovered via `--private-dir`,
`ADVS_PRIVATE_DIR`, then conventional names under the user's Desktop. Nothing
under it is opened for writing.

## Private material

Observations, OCR text and coordinates live in gitignored
`evaluation/private_runtime/`. Real ground truth remains in the gitignored
`evaluation/backend_round2/work/`. Neither is committed.