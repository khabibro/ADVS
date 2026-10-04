# P2 OCR Recognition and Observation Quality

P2 separates the page image, render, detection, recognition, OCR observations,
candidate generation, field resolution, and evidence acceptance. OCR confidence
is not treated as correctness. Raw observation text and private gold remain in
ignored runtime storage; tracked artifacts use safe sample IDs and aggregate
counts only.

## Current status

- Baseline state: `baseline_state.md`
- P1 closure: `../p1_layout/structural_layer_decision.md` and
  `../p1_layout/gpa_gold_review.md`
- Full P2 acceptance is not yet established. No production OCR change is
  approved from P1 evidence alone.
- The seven-document corpus fingerprint matches the frozen P1 manifest.
- Current executable OCR environment is available in `apps/api/.venv312` with
  cached Paddle models. System Python is 3.14 and has no Paddle packages.

No private document, raw OCR string, screenshot, or field value belongs in this
directory.
