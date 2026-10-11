# Evaluation

ADVS evaluation uses only the fictional test-variant dataset:

`evaluation/datasets/synthetic/test_variants/`

The retained Phase B harness runs the real API workflow against a fresh scratch
SQLite database. From the repository root, run a quick digital-only pass with:

```bash
cd apps/api
.venv312/bin/python ../../evaluation/harness/run_variants.py \
  --output ../../evaluation/phase_c/test_variants_digital.json \
  --versions digital --skip-ocr
```

The equivalent Make target is `make eval-variants`. The generated output is a
local run artifact and should not be committed.

The retained reports are in `evaluation/reports/`:

- `ADVS_system_audit_report.md`
- `PHASE_B_REPORT.md`

All legacy datasets, scorers, reports, caches, and scratch results were moved
out of the repository to `~/ADVS_archive_20261004/`. The archive README lists
the original paths and the recovery location for each group.

## Phase reports and write-ups

- `phase_c/`, `phase_d/`, `phase_d2/`: scored runs, injection results and reports of the extraction, auto-acceptance and safety phases (`PHASE_D_REPORT.md`, `PHASE_D2_REPORT.md`).
- `phase_e/`, `phase_e2/`: demo readiness and the interface (`PHASE_E_REPORT.md`, `PHASE_E2_REPORT.md`, `UX_AUDIT.md`).
- `phase_f/`: technical audit, approach evaluation (the existing OCR and deterministic improvements), evaluation protocol with denominators and uncertainty, and two reproducible scripts (`scripts/denominators.py`, `scripts/text_layer_probe.py`).
- Hold-out set 3 is unseen and reserved for the single D3 judgement; do not run or open it.

- `phase_g/`: Phase G gate scripts and results: development-data gates (`results/dev_final/`, `results/gate_summary_dev_final.md`), PDF manipulation suites, `university_replay.py` before/after, the single hold-out 3 judgement (`final/`), and `PHASE_G_REPORT.md`.
