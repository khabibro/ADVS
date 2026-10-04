# Evaluation

ADVS evaluation uses only the fictional test-variant dataset:

`evaluation/datasets/synthetic/test_variants/`

The retained Phase B harness runs the real API workflow against a fresh scratch
SQLite database. From the repository root, run a quick digital-only pass with:

```bash
cd apps/api
.venv312/bin/python ../../evaluation/phase_b/run_variants.py \
  --output ../../evaluation/phase_b/test_variants_digital.json \
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
