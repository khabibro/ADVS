# P2 Changes

## Production

None. Evidence does not currently justify changing the OCR model, rendering,
preprocessing, thresholds, or extraction policy.

## Evaluation artifacts

- Added safe-ID dataset manifest and OCR observation baseline aggregates.
- Added an observation-gold protocol and explicit failure taxonomy.
- Added rendering/preprocessing status, model research, error analysis,
  candidate selection, ablation, performance and safety records.
- Added P1 structural-layer and transcript GPA closure records under
  `evaluation/p1_layout/`.

No dependencies or migrations changed. The real HTTP workflow is unchanged and
reproduces the same field counts as P1. No private OCR text, gold value,
screenshot, or source filename was added to tracked P2 artifacts.
