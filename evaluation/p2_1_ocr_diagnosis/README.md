# P2.1 Observation-Level OCR Diagnosis

## What this phase is

P2 failed because it could not tell six different things apart: detection
failure, recognition failure, downstream extraction failure, candidate
generation failure, field/label association failure, and structural
interpretation failure. This phase builds the missing measurement — an
observation-level ground truth — and then reports where information actually
disappears, one field at a time, with the failing stage named.

**No production code was changed. No OCR setting was changed. Nothing was
committed or pushed.**

## Result in one paragraph

Across the 33 gold-evaluated fields on the frozen 7-document corpus, **zero
detection failures were confirmed**. Every value a human can read was
recovered by the detector. The 17 unresolved fields break down as **6
recognition failures, 4 extraction-path failures, 5 structural-interpretation
failures, and 2 that the document simply does not contain**. The dominant
measured category is **recognition failure**, but it is not dominant enough to
justify an OCR change on its own, because recognition quality is *not* the
binding constraint: fixing every recognition error would still leave 9 fields
unresolved for structural and extraction reasons that no recognizer can fix.

## Reports

| File | Contents |
|---|---|
| `baseline.md` | The frozen P2 baseline, recorded unchanged |
| `dataset_manifest.md` | The seven documents, by safe ID and fingerprint only |
| `observation_matrix.md` | Per-field visibility / detection / recognition / extraction / diagnosis |
| `failure_taxonomy.md` | The taxonomy, the rule order, and the confirmed-vs-not distinction |
| `pipeline_trace.md` | Stage-by-stage trace for every failure |
| `multipage.md` | 1 / 3 / 6 page validation |
| `concurrency.md` | Two documents, two projects, two threads |
| `safety.md` | Safety matrix and the one wrong non-null value |
| `quality.md` | Every quality gate, with results |
| `final_report.md` | Verdict, the ten required answers, and what P2.2 should do |

## Scripts

All scripts are read-only with respect to the corpus and write only to the
gitignored `evaluation/private_runtime/p2_1/`.

| Script | Purpose |
|---|---|
| `inventory_dataset.py` | Read-only corpus inventory and fingerprint check |
| `capture_observations.py` | Runs the unmodified production OCR entry point and dumps observations |
| `annotate_pages.py` | Renders the annotation surface (coordinate grid, OCR overlay) |
| `build_observation_matrix.py` | Joins gold + observations + frozen gold and classifies |
| `probe_structural_layer.py` | Evaluation-only probe of the dormant structural layer |
| `run_workflow_probe.py` | Real-OCR HTTP workflow plus the safety matrix |
| `run_multipage_concurrency.py` | Multipage and concurrency validation |

## Private data

Ground truth, OCR text, extracted values and rendered overlays live in
`evaluation/private_runtime/p2_1/`, which `.gitignore` covers. Nothing in this
directory contains a private filename, path, OCR string, name, identifier or
address. The seven originals were fingerprinted before and after and are
byte-identical with unchanged mtimes.
