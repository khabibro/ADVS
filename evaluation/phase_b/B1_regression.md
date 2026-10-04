# B1 Regression — Real Corpus and Mentor Synthetic Set

## Real corpus (REAL-001..007)

**Could not be freshly re-run.** `evaluation/backend_round2/run_round2.py`
resolves its source documents from `~/Desktop/Samples/` (or `Samples/` or
`SAMPLES/`) by design. That folder no longer exists on this machine --
confirmed by listing `~/Desktop/` directly, which now contains only
`khabibillo/` (the user's unrelated separate repository checkout). This is
not a Phase B regression; the folder was relocated/removed in a later
session than the one that produced `BASELINE_B0_pre_safety.md`, outside
this phase's control. Attempting the run produces
`FileNotFoundError: Could not resolve '4대 사회보험료 완납증명서.pdf' in
any Desktop sample directory` -- shown here rather than worked around, per
instruction not to fabricate a result.

**What can be said without re-running, and on what basis (inference, not
measurement):**

B-1 through B-4 touch only validation rules (`validation/engine.py`,
`validation/submission.py`, `services/document_validation.py`,
`services/requirements.py`) and the classifier's look-alike guard
(`classification/classifier.py`). None of them touch extraction,
normalization, or OCR. Consequences for the REAL-001..007 field-level
score specifically:

- **Field values (CORRECT / INCORRECT / UNRESOLVED against gold v3) are
  unaffected.** The scorer (`evaluation/backend_round2/summarise.py`)
  compares extracted field *values*, which no part of this phase changes.
  The Phase A baseline (`B0_score_v2_vs_v3.json`) -- CORRECT 16, INCORRECT
  1, UNRESOLVED 18, evaluated-field denominator 35 under gold v3 -- should
  be reproduced exactly if re-run against a working source folder. This is
  an inference from reading the diff, not a re-measurement, and is stated
  as such.
- **Classification (7/7 correct in the Phase A baseline) is unaffected
  specifically for this corpus.** B-3's new `UNSUPPORTED_LOOK_ALIKE_TITLES`
  check only fires on text containing `지방세납세증명서`, `휴학증명서`, or
  `졸업예정증명서` (checked directly against the table in
  `classification/classifier.py`) -- none of REAL-001..007's genuine
  document types (per `evaluation/p2_1_ocr_diagnosis/dataset_manifest.md`:
  social insurance, business registration, two transcripts, two enrollment
  certificates, one SME confirmation) match any of those three markers, so
  the new check cannot change their classification outcome.
- **False READY (0 in the Phase A baseline) is not directly re-verified**
  for this corpus at the submission level in this phase -- the Phase A
  baseline measured field-level and document-classification correctness,
  not a full checklist-driven submission status for REAL-001..007. This
  was already outside what Phase A measured; Phase B does not newly verify
  or newly risk it.

**Acceptance criterion verdict:** the two numeric criteria ("CORRECT not
lower, WRONG non-null not higher than baseline" and "False READY 0") are
assessed **PASS by code-path analysis**, not by fresh measurement, for the
reasons above. This is stated plainly as a methodological gap, not papered
over: if the source folder becomes available again, re-running
`run_round2.py` + `summarise.py` against gold v3 is the direct check, and
should reproduce `B0_score_v2_vs_v3.json`'s gold-v3 numbers unchanged.

## Mentor synthetic set

**Still NOT REPRODUCIBLE**, unchanged from the Phase A baseline, for the
same reason recorded there: `apps/api/scripts/eval_phase5_mentor.py`'s
source folder (`~/Desktop/학생용_가상데이터/`) does not exist in this
environment. Not re-checked in this phase beyond confirming the Phase A
finding still holds (Desktop listing above). No substitute dataset was
used for this claim, per instruction.
