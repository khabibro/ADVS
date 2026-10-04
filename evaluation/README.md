# ADVS Evaluation Toolkit (P1.5+)

Measures the document-intelligence pipeline (classification, extraction,
normalization, validation) against a benchmark, with evidence-based
improvement rather than untested tuning.

- `evaluation/reports/baseline_2026-09-09.md` / `final_2026-09-09.md` -- the
  original P1.5 baseline (112 purely-synthetic samples) and its fixes.
- `evaluation/reports/source_research.md` -- deep research into real
  official/institutional sources for all four document types (government
  portals, an official legal-database, university registrars, HR/legal
  vendor blogs), recorded in `evaluation/sources/source_registry.json`.
  **No third-party binary file was downloaded or stored** -- every source's
  disposition is `RECREATE_ONLY` (see that file's policy statement).
- `evaluation/reports/baseline_2026-09-09b.md` / `final_2026-09-09b.md` --
  the follow-up baseline after extending the benchmark with
  research-motivated recreations, an expanded negative set, and
  cross-document submission bundles, and the fixes *that* baseline
  motivated (including a real false-PASS finding -- see "Changes made"
  in that report).

## Four sample categories -- never mixed in a report

- **`SYNTHETIC_REALISTIC`** (`evaluation/datasets/synthetic/`,
  `evaluation/gold/synthetic/`): deterministically generated (seed 42,
  `apps/api/scripts/eval_generate.py`), safe to commit, safe to regenerate.
- **`RECREATED_FROM_PUBLIC_REFERENCE`** (`evaluation/datasets/recreated/`,
  `evaluation/gold/recreated/`): from-scratch recreations (fictional data
  throughout) that specifically exercise real-world label vocabulary or
  document titles found during source research -- each cites a `source_id`
  in `source_registry.json`. Never call these "real documents."
- **`NEGATIVE_OUT_OF_SCOPE`**: UNKNOWN-gold samples, including several
  using real out-of-scope document terminology found during research
  (재학증명서, 성적증명서, 재직증명서, 사업자등록증명원) alongside synthetic
  negatives. Currently filed under `datasets/synthetic/unknown/` (this
  repo's existing negative-sample location; not duplicated into a separate
  `datasets/negative/` directory).
- **`OFFICIAL_PUBLIC_REFERENCE`** (an actual downloaded public file, stored
  verbatim): **none exist**. See `make eval-public`.
- **Real** (`evaluation/datasets/real/`, `evaluation/gold/real/`): properly
  anonymized real documents or authorized templates, gitignored by default,
  requires human-verified gold labels before being scored. See
  `evaluation/datasets/real/README.md`. **None exist yet** -- pending.

A sample's `source_class` field in its gold label (schema v1.1) records
which of the first three applies. Every report states which categories it
covers; a synthetic or recreated result is never presented as "real-world
accuracy."

## Two evaluation modes

- **Mode A / "mock"** (default): scores classification/extraction/validation
  against gold OCR text directly -- no OCR provider involved. This is what
  most of the numbers in this toolkit are. It tests the deterministic
  heuristics in isolation, not OCR behavior.
- **Mode B / "paddle"**: sends the actual rendered file through PaddleOCR,
  then scores the same way Mode A does. It is opt-in and never run from
  `make check`/`make check-all`/CI because model downloads and CPU inference
  are too heavy for the normal quality gate. If PaddleOCR is unavailable or
  all samples fail, the result is marked `NOT_RUN` rather than treated as an
  accuracy score.

## Directory layout

```
evaluation/
  README.md                  -- this file
  manifest.json               -- every per-document sample: id, paths, split, source
  submissions_manifest.json   -- N/A: bundles are defined in code (eval_lib/submissions.py)
                                  and reference existing sample_ids, not separate files
  sources/
    source_registry.json       -- provenance for every researched source (RECREATE_ONLY)
  datasets/
    synthetic/<type>/*.txt     -- gold OCR text (source of truth)
    synthetic/<type>/*.pdf|png|jpg  -- rendered file for format/quality coverage
                                       and PaddleOCR input
    recreated/<type>/*.txt|.pdf|.png|.jpg  -- RECREATED_FROM_PUBLIC_REFERENCE samples
    real/inbox/                -- drop new real files here
    real/unlabeled/             -- ingested, not yet labeled
    real/README.md              -- privacy policy and labeling workflow
  gold/
    synthetic/*.json           -- versioned gold labels (schema v1.1)
    recreated/*.json            -- same schema, source_class=RECREATED_FROM_PUBLIC_REFERENCE
    real/*.json                 -- gitignored; human-verified before scoring
  results/                     -- JSON + CSV per run (fully tracked)
  reports/                     -- Markdown reports (fully tracked)
  cache/                       -- reserved for future local evaluation caches
```

`evaluation/results/` and `evaluation/reports/` have no `.gitignore` entry —
every file in both, including routine per-run output, is tracked
unconditionally (verified 2026-10-04: 44 and 7 tracked files, 0 untracked).
The frozen baseline/final files
(`baseline_2026-09-09*`, `final_2026-09-09*`, `baseline_2026-09-09b*`,
`final_2026-09-09b*`) still carry the same do-not-overwrite rule as before —
do not delete them, and never overwrite a `baseline_*` file with a later
run — but that rule is about discipline, not `.gitignore`.

Submission bundles (cross-document, project-level validation) are not a
separate file-based dataset: `apps/api/scripts/eval_lib/submissions.py`
defines each bundle in code, referencing the `subdoc_*` sample_ids that
`eval_generate.py` produces (dedicated fixtures with controlled applicant/
company identity for name/company-match and duplicate-detection testing).
Run `make eval-submissions` after `make eval-generate`.

## Phase history (`evaluation/<phase>/`)

Everything below `datasets/`, `gold/`, `results/`, `reports/`, `baselines/`,
`sources/`, and `cache/` (documented above) is the **wired toolkit** — driven
by `make eval-*`/`make baseline*` and described in this file. Every other
top-level directory under `evaluation/` is a **phase-history directory**:
a self-contained, tracked set of Markdown reports (and, for the real-document
phases, scripts) produced by one investigation phase of this capstone
project. None of these are wired into `Makefile` or run by any command —
they are read, not executed, and are kept as the project's evidentiary
record. Ordered roughly by when each phase's own reports say the work
happened (git history on `main` is compressed into a handful of batched
commits, so commit dates are not a reliable ordering — several phases'
work was committed together well after it was done):

| Directory | Phase | What it is |
|---|---|---|
| `phase5/`, `phase6/` | Phase 5/6 | Early frontend-adjacent audit phases (~2026-09-22) |
| `phase7/` | Phase 7 | Follow-on audit phase (~2026-09-28) |
| `backend_audit/` | — | OCR/DPI ablation audit; `work/` subfolder is gitignored (rendered pages from a real scan) |
| `phase8/` | Phase 8 | Frontend audit baseline (~2026-09-29) |
| `astra_backend/` | — | Architecture-options research/comparison (dated 2026-09-29/30 in-report) |
| `real_backend_validation/` | — | Independent real-document backend readiness audit (dated 2026-09-30 in-report) |
| `p0_backend/` | P0 | Backend stabilization evidence (sanitized; samples addressed only by `DS-0xx`/`R2-0x`/`REAL-00x` ids) |
| `p1_layout/` | P1 | Structural layout layer (dormant — see `docs/architecture/ARCHITECTURE.md` known limitations) |
| `p2_1_ocr_diagnosis/` | P2.1 | OCR diagnosis for the mentor-defined document domain |
| `p2_ocr/` | P2 | OCR-focused follow-up work |
| `p2_2_targeted_improvement/` | P2.2 | Targeted-improvement scripts (gitignored as a whole directory — one script hardcodes transcribed real-document values; see `.gitignore`) |
| `backend_round2/` | P2.1 (this session) | Real-corpus (REAL-001..007) adjudication round 2; `work/` subfolder is gitignored (real ground truth, diagnostics) — see "Gold label versions" below |
| `system_audit/` | — | Independent full-system audit (this session) |
| `phase_a_baseline/` | Phase A (this session) | Clean, reproducible baseline — `BASELINE_B0_pre_safety.md` is the precondition file every later phase checks for |
| `cleanup/` | Cleanup/docs (this session) | This inventory and the `docs/` rewrite it precedes |

Phase B (`evaluation/phase_b/`: four safety-fix measurements, before/after)
exists only on the unmerged branch `phase-b/safety-fixes` — intentionally
not part of `main` or this list until it is reviewed and merged.

## Gold label versions — two separate systems, do not confuse them

1. **Synthetic/recreated gold** (`evaluation/gold/synthetic/`,
   `evaluation/gold/recreated/`, schema v1.1, documented below) — one JSON
   file per generated sample, versioned only in the sense that the schema
   itself has a version field. This is what `make eval-*` scores against.
2. **Real-document round 2 gold** (`evaluation/backend_round2/work/
   ground_truth*.json`, gitignored — real names/ids, never committed) —
   a *different*, independently-evolving set of hand-adjudicated labels for
   the 7-document real corpus (`REAL-001..007`, internally keyed `R2-01..
   R2-07`). It has its own version history, unrelated to the schema
   version above:
   - **v1** (`ground_truth.json`) — first transcription pass.
   - **v2** (`ground_truth_v2.json`) — frozen for this session's P2.1
     adjudication; used as Phase A's `B0` baseline comparison point.
   - **v3** (`ground_truth_v3.json`, under `evaluation/private_runtime/`)
     — this session's adjudication of 3 disputed fields (REAL-003/`gpa`,
     REAL-003/`gpa_scale`, REAL-004/`department`), re-derived from the
     original document images rather than OCR, which also changed the
     evaluated-field denominator from 33 to 35. See
     `evaluation/backend_round2/` and `evaluation/phase_a_baseline/
     BASELINE_B0_pre_safety.md` for the full adjudication record and
     citation (safe ids and the id map only — no field values are
     reproduced in any tracked file).

## Gold label schema (v1.1)

One JSON file per sample, field vocabulary identical to
`app.core.domain.EXPECTED_FIELDS` (no competing field names):

```json
{
  "schema_version": "1.0",
  "sample_id": "business_registration_003",
  "source": "synthetic",
  "document_type": "BUSINESS_REGISTRATION_CERTIFICATE",
  "input_format": "scanned_pdf",
  "quality": "clean",
  "layout_variant": "vertical",
  "split": "dev",
  "fields": {
    "company_name": {"value": "테스트테크 주식회사", "required": true},
    "business_registration_number": {"value": "903-83-10111", "required": true}
  },
  "expected_validation_status": "READY",
  "notes": "label spacing variant applied",
  "verified": true,
  "source_class": "SYNTHETIC_REALISTIC",
  "source_id": null
}
```

`verified: false` means "not yet human-confirmed" -- only ever the default
for freshly-ingested real samples; every synthetic/recreated sample is
generated already-correct-by-construction (`verified: true`), since the
generator produces the text and the label from the same values.
`source_id` (when set) references an entry in
`evaluation/sources/source_registry.json`.

## Commands

| Command | What it does |
|---|---|
| `make research-sources` | Points at the research report/registry (research itself is manual/interactive) |
| `make eval-generate` (= `dataset-recreate`, `dataset-variants`) | Regenerates the full benchmark: synthetic + recreated + negatives + submission fixtures (deterministic, seed 42) |
| `make eval-synthetic` | Mode A run on the `dev` split (all source classes) |
| `make eval-held-out` | Mode A run on the `held_out` split (never used to tune anything) |
| `make eval-recreated` | Mode A run scoring only `RECREATED_FROM_PUBLIC_REFERENCE` samples |
| `make eval-public` | Prints `NOT APPLICABLE` -- no downloaded public files exist by policy |
| `make eval-submissions` | Cross-document, project-level validation (10 bundles: READY/missing-doc/expired/name-mismatch/company-mismatch/duplicate/REVIEW_REQUIRED/ambiguous-doc) |
| `make eval-paddle` | Mode B: real PaddleOCR over renderable benchmark samples |
| `make eval-report` | Builds `evaluation/reports/latest.md` from the latest dev+held-out runs |
| `make eval` | generate + dev + held-out + report, in one step |
| `make baseline-fast` | Phase 0 smoke baseline: deterministic one-sample-per-document-type subset through gold text and PaddleOCR |
| `make baseline` | Phase 0 full baseline: regenerates the benchmark, runs gold text and PaddleOCR, fingerprints the dataset, and writes consolidated JSON/Markdown snapshots |
| `make eval-ingest` | Ingests `evaluation/datasets/real/inbox/` into the manifest (unverified) |
| `make eval-label` | Lists real samples awaiting human labeling |

None of these are part of `make check`/`make check-all` -- they are a
separate, on-demand measurement workflow, not a CI gate. They are safe but
are not about code correctness; they measure pipeline quality.

## Phase 0 baseline workflow

Phase 0 treats the current implementation as `baseline_v0`. It does not tune
OCR, extraction, classification, or validation. It records what the current
system does so later architectures can be compared against the same dataset
and metric definitions.

Run:

```bash
make baseline-fast
make baseline
```

`make baseline-fast` is a deterministic smoke run. `make baseline` is the full
measurement pass. Both commands compose the existing evaluator and write:

- `evaluation/results/baseline_v0*.json` -- machine-readable consolidated result.
- `evaluation/baselines/baseline_v0*.json` -- named baseline snapshot.
- `evaluation/baselines/baseline_v0*.md` -- human-readable report.

The baseline snapshot includes environment metadata, Paddle/PaddleOCR
versions, model names, git commit and dirty state, dataset distributions,
per-file dataset SHA-256 values, an overall dataset fingerprint, metric
definitions, gold-text metrics, PaddleOCR metrics, false-READY counts and
sample IDs, failure categories, and gold-vs-OCR gap tables.

Gold-text and PaddleOCR results must stay separate:

- **Gold text** isolates deterministic classification, extraction,
  normalization, and validation from OCR.
- **Real PaddleOCR** measures the actual current rendered-document path:
  PaddleOCR -> normalized OCR text -> classification -> extraction ->
  validation.

False READY is safety-critical. It means a validation-labeled sample whose gold
status is not `READY` was predicted as `READY`. Future improvements may increase
field accuracy, but they must not silently increase false READY.

## Metric definitions

- **OCR CER**: Levenshtein distance over whitespace-stripped gold OCR text
  divided by gold character count.
- **OCR text similarity**: `difflib.SequenceMatcher` ratio over
  whitespace-stripped gold OCR text and PaddleOCR text.
- **Classification accuracy**: samples with predicted document type equal to
  gold document type divided by scored samples.
- **Field accuracy**: required fields whose normalized predicted value exactly
  equals normalized gold value divided by required fields.
- **Document-level extraction success**: supported-document samples where every
  required field is correct divided by supported-document samples.
- **Validation accuracy**: validation-labeled samples where predicted status
  equals gold status divided by validation-labeled samples.
- **False READY count/rate**: non-`READY` gold samples predicted as `READY`,
  plus that count divided by validation-labeled samples.
- **REVIEW rate**: classification `needs_review` count divided by scored
  samples.

Metrics not supported by available labels are reported as `NOT AVAILABLE`
rather than fabricated. Real/anonymized evaluation remains unavailable until
verified files and labels exist under `evaluation/datasets/real/` and
`evaluation/gold/real/`.

## Train/dev/held-out discipline

Synthetic/recreated samples are split 70/30 (`dev`/`held_out`) deterministically
by sample index (105 and 32 samples respectively as of the latest generation).
Fixes are only ever motivated by `dev` failures; `held_out` is re-scored
afterward to check the fix generalizes, and is never used to choose what to
fix. Both are still small -- treat any single-digit-sample-count metric as
indicative, not conclusive. Submission bundles (10) are a fixed set used the
same way in both directions (not tuned against a held-out subset of
themselves, since there are too few to split meaningfully).

## What "confidence" and "accuracy" mean here

Classification `confidence_score` is a heuristic evidence ratio (see
`docs/domains/classification.md`), not a calibrated probability. All
"accuracy" figures in this toolkit's reports are against the **synthetic**
benchmark unless a report section explicitly says "real" or "PaddleOCR
end-to-end" -- and as of this writing, no real-document run has occurred
(see `evaluation/datasets/real/README.md`).
