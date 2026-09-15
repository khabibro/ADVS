# Real / anonymized evaluation documents

**This directory is gitignored except this README and the `.gitkeep`
placeholders.** Nothing placed here is committed automatically.

## What belongs here

- Properly anonymized real Korean administrative documents, OR
- Official/public blank/example templates you have the right to use, OR
- Manually supplied safe samples you have created yourself.

Do **not** place here (and this project will never fetch on its own):

- documents scraped or downloaded from the internet,
- leaked or exposed personal documents,
- documents containing a real resident registration number or other
  identifier you are not authorized to hold,
- anything you would not be comfortable existing on this machine's disk
  outside of version control.

## Workflow

1. Drop files into `evaluation/datasets/real/inbox/`.
2. Run `make eval-ingest` (`apps/api/scripts/eval_ingest.py`). This:
   - assigns each file a safe sequential sample ID (`real_0001`, ...),
   - validates the file is a supported, non-corrupt format,
   - copies it to `evaluation/datasets/real/<document_type_unknown>/` (initially
     filed under `unlabeled/` until a human assigns a type),
   - creates an **unverified** gold-label template in `evaluation/gold/real/`
     with `"verified": false` and every field set to `null`.
3. Run `make eval-label` (`apps/api/scripts/eval_label.py`) to see the list of
   unverified labels and, for each one, open the gold-label JSON, fill in the
   real values by looking at the actual document, and set `"verified": true`.
   **A pipeline prediction is never auto-copied into a gold label as if it
   were ground truth** -- `eval_label.py` will show you the document text
   path but will not write predicted values into the gold file for you.
4. Once labels are verified, re-run `apps/api/scripts/eval_generate.py`'s
   sibling manifest step is not needed for real samples -- `eval_ingest.py`
   registers them directly into `evaluation/manifest.json` with
   `"source": "real"`, so `eval_run.py` picks them up automatically.

## Why "unverified by default"

A wrong gold label is worse than no gold label -- it would make a correct
pipeline prediction look like a failure, or a wrong one look like a success.
`eval_run.py` and `eval_report.py` never treat an unverified real label as
scorable ground truth.
