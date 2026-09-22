# Phase 5 mentor evaluation

This directory records controlled evaluation of the 32 in-scope mentor
synthetic raster PDFs. The six local-tax PDFs are discovered but excluded.
Mentor binaries are never copied into this repository.

Run from `apps/api`:

```bash
.venv312/bin/python scripts/eval_phase5_mentor.py \
  --output ../../evaluation/phase5/final_summary.json
```

The evaluator locates the Unicode-normalized mentor folder under the current
user's Desktop and exercises the real HTTP upload, storage, processing,
persistence, and read path using an isolated temporary database and storage
directory. It stores no filenames, OCR text, raw field values, normalized
field values, or identity values. Short normalized-value fingerprints allow
regression comparison without exposing the values.

The mentor README supplies document-type/scenario truth but no exact field
values. Consequently, these artifacts report classification accuracy,
expected-field completeness, normalization-shape validity, and provenance.
Exact field correctness and incorrect-populated-value counts are explicitly
`NOT_EVALUATED`; they must not be inferred from completeness.

`baseline_summary.json` is immutable and represents Phase 4 behavior before
production extraction changes. `final_summary.json` uses the identical method
after Phase 5 hardening. `comparison.json` records the metric deltas and
fingerprint-based regression check. `error_analysis.json` records the
structural causes and final remaining failures.
