# ADVS — P0 Final Validation Report

## A. Executive verdict

**P0_PASS_WITH_WARNINGS**

P0 is a stabilisation phase and on that basis it is accepted. Every reliability
and safety metric on the owner's own document corpus improved or held: upload
acceptance, processing completion, classification accuracy, field recall, and
False READY, which fell from 3 to 0. Backend and frontend gates are green.

The warnings are real and are not dismissed:

1. **One wrong non-null value.** A personal name was extracted from a scanned
   transcript at 0.917 OCR confidence and does not match the document. It is
   contained by the evidence policy and cannot reach `READY`, but it is a real
   defect and the highest-priority item carried into the next phase.
2. **P0 introduced a false rejection, which this validation found and fixed.**
   The resource budgets added during P0 rejected a legitimate corpus document
   outright. See section K.
3. **Recall remains low** (0.471) and the dominant causes are table and layout
   problems, which are P1 by definition.
4. **Three of eight supported document types are unexercised** by real input.

## B. Repository

| Field | Value |
|---|---|
| Starting HEAD | `f641fee2031641f3da0983d57d27460607c7f89e` |
| Final HEAD | see section AC |
| Branch | `main` |
| Author | `KHABIBILLO <khabibillionaire@gmail.com>` |
| Remote | `git@github-khabibro:khabibro/ADVS.git` |
| Push account | `khabibro` (confirmed by `ssh -T`) |

## C. Desktop samples

| Question | Answer |
|---|---|
| Folder located | yes |
| Total files | 7 |
| Unique SHA-256 | 7, no duplicates |
| Supported samples | 7 |
| Out-of-scope samples | 0 |
| PDFs | 3 |
| Images | 4 |
| Single-page | 7 |
| Multi-page | 0 |
| Scanned | 7 |
| Born-digital | 0 |

Every sample is an image-only scan; none carries an embedded text layer. No
absolute Desktop path is recorded in any committed artefact.

The originals were treated as read-only throughout. SHA-256, size, mode and
modification time were captured before and after the entire evaluation and are
identical. No sample was renamed, moved, copied into the repository, modified or
deleted.

## D. Historical dataset relationship

| Question | Answer |
|---|---|
| Exact historical matches | **7 of 7** |
| New samples | 0 |
| Unknown provenance | 0 |

Every sample matches by SHA-256 both the recorded real-document inventory and
the round-2 frozen manifest. Each sample therefore carries three consistent
internal ids referring to the same bytes.

Because all seven are exact matches, **Track A and Track B cover the same
files**. Track A asks whether P0 changed behaviour, measured by re-running the
identical harness against `721cc9d`. Track B asks how the current system
behaves on the corpus, under this phase's manual ground-truth rules. Both use
the same frozen gold and the same scorer, so they are directly comparable. There
is no separate new-sample cohort.

## E. Current accuracy

| Metric | Value |
|---|---|
| Documents processed | 7 of 7 |
| Classification correct | 7 |
| Classification incorrect | 0 |
| `UNKNOWN` | 0 |
| Fields `CORRECT` | 16 |
| Fields `INCORRECT_NON_NULL` | 1 |
| Fields `UNRESOLVED` | 17 |
| Fields `VERIFIED_ABSENT` handled | 2, both abstained correctly |
| `HALLUCINATED_EXTRA_FIELD` | 0 |
| Fields `NOT_EVALUATED` | 7 |
| Field precision | 0.941 |
| Field recall | 0.471 |

No field was produced outside the extractor's supported set for its classified
type. A `VERIFIED_ABSENT` field was never scored as a successful extraction, and
in both such cases the pipeline correctly produced nothing.

## F. Safety

| Metric | Value |
|---|---|
| **False READY** | **0** |
| Documents reaching `READY` | 0 of 7 |
| Null-derived mismatch | 0 |
| Null-derived expiry | 0 |
| Hallucinated values | 0 |
| Negative-assertion violations | 0 |
| Wrong non-null values | 1 (gated, cannot reach `READY`) |
| Review burden | 3–4 items per document; 7 of 7 documents need review |

Safety and accuracy are reported separately and are not combined into one score.
The system is safe and imprecise on this corpus, not the reverse.

## G. Per-type results

| Document type | Real samples | Classified | Fields correct | Notes |
|---|---|---|---|---|
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | 1 | correct | 2 of 4 | `valid_until` correctly abstained |
| BUSINESS_REGISTRATION_CERTIFICATE | 1 | correct | 1 of 2 | address/type/item not evaluated |
| TRANSCRIPT | 2 | correct | 4 of 12 | GPA table is the main failure |
| ENROLLMENT_CERTIFICATE | 2 | correct | 3 of 10 | university/department unresolved in both |
| SME_CONFIRMATION_CERTIFICATE | 1 | correct | 4 of 4 required | strongest document in the corpus |
| GRADUATION_CERTIFICATE | 0 | — | — | unexercised by real input |
| CAREER_CERTIFICATE | 0 | — | — | unexercised by real input |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | 0 | — | — | unexercised by real input |

## H. Failure taxonomy

Counts over the 17 unresolved fields plus the one wrong value.

| Category | Count | Notes |
|---|---|---|
| TABLE_STRUCTURE | 5 | course-table GPA; total versus per-block figures |
| LAYOUT_LOSS | 5 | header-band labels, multi-line body text not collapsed |
| ROW_GROUPING | 3 | label and value in distant table cells |
| CANDIDATE_SELECTION | 2 | several conflicting candidates; abstains |
| CONFIDENCE_POLICY | 1 | below the evidence threshold |
| OCR_RECOGNITION | 2 | the wrong name; one illegible field |
| FIELD_SCHEMA | 0 | no missing-field failures |
| VALIDATION | 0 | no false mismatch, no false expiry |
| Normalisation | 0 | no normalisation-caused failure |
| OTHER | 0 | — |

Nothing in this taxonomy points at the safety layer.

## I. Wrong non-null values

One. Analysed without exposing the value.

| Question | Answer |
|---|---|
| Sample | one scanned transcript |
| Document type | TRANSCRIPT |
| Field | personal name |
| OCR confidence | 0.917 |
| Evidence state | 5 OCR observations, page 1, assessment `REVIEW_REQUIRED` |
| Fed to a deterministic rule | **no** — policy-gated to null before the rule engine |
| Verification impact | contributes to `REVIEW_REQUIRED` only |
| Human review path | yes, offered in the review queue |
| Could cause a false `READY` | **no** |
| Could cause a false correction | **no** — no deterministic rule consumed it |
| Root cause | OCR_RECOGNITION, with a spatial right-of-label pairing that picked the wrong adjacent column |

**The important point: OCR confidence is not semantic correctness.** A 0.917
recognition confidence on a wrong value is still wrong, and it is wrong at a
higher confidence than several values that happened to come out right. The
containment here comes from the evidence policy, not from the confidence
threshold. Lowering the threshold would not have caught it; only independent
human confirmation does.

This is the highest-priority accuracy defect carried forward.

## J. Evidence quality

For every populated field, evidence was checked for page correctness, source
correctness and whether the cited OCR text actually supports the value.

- Page references correct on all populated fields.
- The wrong name carries **truthful provenance**: the cited OCR observations are
  real, on the right page, and genuinely say what was reported. Extraction and
  recognition are wrong; the evidence trail is honest. These are recorded
  separately rather than conflated.
- No value was linked to the wrong source.
- All seven corpus documents are image-only, so **every** machine value is
  OCR-sourced and therefore requires human confirmation before use. No
  `embedded_pdf_text` evidence exists in this corpus, so the digital-PDF evidence
  route is unexercised.

## K. F-01 — upload resource validation

**PASS after fixing a P0 regression found during this validation.**

Storage no longer projects OCR render resolution onto the PDF page box, so a
legitimate large-page document is not rejected for a downstream rendering
concern.

However, the P0 work had introduced a **new false rejection**: the per-page
pixel budget was applied to the page box at 288 DPI, so a 1117×1408 pt page
carrying a 72 DPI scan rendered to 25,163,776 px against a 25,000,000 budget —
**0.65 % over** — and was rejected with `RESOURCE_LIMIT`, failing in 14 ms. The
PRE-P0 pipeline had processed that document successfully.

Fix: render such a page at the resolution its own embedded raster justifies, but
never below it, and only when the configured scale would breach the budget.
Pages already within budget are unchanged, and vector pages are never
downscaled. The decision and its reason are recorded in page metadata.

| Document | Before | After |
|---|---|---|
| DS-001 | 25.16 MP, rejected | 3.54 MP, processed |
| DS-004 | 8.02 MP | 8.02 MP, unchanged |
| DS-007 | 8.02 MP | 8.02 MP, unchanged |

Three regression tests added. The fix encodes no sample value, dimension or
filename.

## L. F-03 — issue date

**PASS.** Valid local issue dates are extracted. A footer carrying an
issue-date-like label no longer suppresses a valid unlabelled date in the
issuance block. Conflicting bare dates abstain rather than picking one. An
inferred date is always flagged for review. Four of seven documents yielded a
correct issue date; the remainder abstained.

## M. F-04 — compound labels

**PASS.** Longer, more specific labels are matched before overlapping shorter
ones, and results no longer depend on alias declaration order: the same value is
produced with the compound alias declared first and last.

## N. F-13 — concurrent OCR

**PASS.** Three concurrent OCR calls on one provider and three concurrent
documents on the live server, plus four concurrent process calls on one document.
No `OCR_BUSY` anywhere. Contention produces waiting, never a terminal failure.

## O. F-14 — timeout and capacity

**PASS.** Timeout is per page, not per document. 1-, 3- and 6-page documents all
completed, with time scaling with page count (16.5 s, 31.1 s, 64.0 s), so no
whole-document ceiling applies. Page provenance and ordering correct on every
page. After a forced timeout the next document processed normally, so no stuck
lock, stuck semaphore or poisoned worker.

## P. F-15 — logging

**PASS.** With production logging configured, application log lines remained
visible before PaddleOCR initialisation, during real OCR and after it. Raising
the root logger to WARNING did not silence application logs.

## Q. F-16 — review closure

**PASS.** Across all eight supported document types, the count of extracted-but-
unreviewable fields is **0**. Optional fields stayed optional; no optional field
became required. All four review decisions behave correctly, stale reviews are
refused with 409, and a corrected value becomes effective with source
`HUMAN_CORRECTED`, which is what lets a reviewer clear an OCR gate.

## R. F-17 — comparison semantics

**PASS.** Safe whitespace differences do not produce a mismatch; genuinely
different values still do; there is no fuzzy matching. Null on both sides yields
no mismatch and no expiry. One documented asymmetry between document scope and
submission scope is recorded in `security_regression.md` and left as a design
question for a later phase.

## S. Live HTTP

**PASS.** A normal local stack was driven only through real HTTP endpoints. All
seven corpus documents completed the full sequence upload → storage → processing
→ OCR → classification → extraction → evidence → persistence → verification →
re-fetch. Re-fetch returned exactly what was persisted in all seven cases. No
document reached `READY`. Review submission, stale-version rejection and
value validation all behaved correctly over HTTP.

## T. Multi-page

| Pages | Pages returned | Ordering | Wall time |
|---|---|---|---|
| 1 | 1 | correct | 16.5 s |
| 3 | 3 | correct | 31.1 s |
| 6 | 6 | correct | 64.0 s |

Recovery after a forced timeout: the next document processed normally. These
are mechanical fixtures; no extraction-accuracy claim is made from them.

## U. Concurrency

| Scenario | Documents | Result |
|---|---|---|
| Distinct documents, live server | 3 | all accepted, all completed, no `OCR_BUSY` |
| Same document, concurrent process calls | 1 | all 200, converged to `COMPLETED`, no duplicate rows, version monotonic |
| Concurrent OCR on one provider | 3 | all returned text, queued behind one slot |

## V. Business workflow

**NOT_EVALUATED_COMPLETE_PACK**, with a partial result.

The corpus contains a business registration certificate, an SME confirmation
certificate and a social insurance payment certificate. It does **not** contain
a national tax payment certificate, so the complete four-document pack cannot be
constructed and no complete-pack result is claimed. Nothing was synthesised to
fill the gap.

The three-document partial submission was evaluated over HTTP:

- status `NEEDS_CORRECTION`
- codes `MISSING_REQUIRED_DOCUMENT`, `OCR_UNCERTAIN`, `REQUIRED_FIELD_UNRESOLVED`
- the missing-document code is **correct** behaviour: the configured checklist
  requires the absent certificate

Business-number matching and workplace-name comparison were exercised
structurally through the verification engine with synthetic values and behaved
correctly, including null safety. They were **not** exercised end-to-end on a
real matching business pack, and no such claim is made.

## W. Student workflow

**PARTIALLY EVALUATED.** A real enrollment certificate and a real transcript were
submitted together over HTTP: status `REVIEW_REQUIRED`, codes `OCR_UNCERTAIN`
and `REQUIRED_FIELD_UNRESOLVED`. The configured issue-date criterion is active
for both types.

GPA remains configurable and optional in the domain model. The transcript
extracts it as a supported field; its failure on the course-table document is a
table-structure limitation, not a schema error. The transcript is not made
required merely by existing.

## X. UNKNOWN handling

**PASS.** A synthetic out-of-scope document was processed end to end. It
classified as `UNKNOWN`, produced **zero** fields and zero populated values, and
its submission ended `REVIEW_REQUIRED` with `UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW`.
No forced classification, no invented fields, no `READY`.

## Y. Security

Ten hostile upload probes over HTTP: eight rejected with typed error codes
(`EMPTY_FILE`, `INVALID_FILE_TYPE`, `TOO_MANY_PAGES`, `CORRUPT_DOCUMENT`). The
two accepted cases were verified correct: a traversal filename was sanitised,
confined to the storage root, stored byte-identical and still classified
correctly; and a PDF declared with the wrong content type was stored and
processed as the PDF it is, because bytes are trusted over client claims. No
partial-file residue, no traversal escape. `pnpm env:validate` and
`pnpm security:audit` both pass.

## Z. Quality gates

| Gate | Result |
|---|---|
| `git diff --check` | PASS |
| `ruff format --check .` | PASS |
| `ruff check .` | PASS |
| `mypy --explicit-package-bases app` | PASS |
| `pytest` | PASS — 350 passed |
| `pnpm env:validate` | PASS |
| `pnpm security:audit` | PASS |
| `make migration-check` | PASS |
| `make docker-check` | PASS |
| `pnpm --filter @advs/web lint` | PASS |
| `pnpm --filter @advs/web typecheck` | PASS |
| `pnpm --filter @advs/web test` | PASS — 94 passed |
| `pnpm --filter @advs/web build` | PASS |

## AA. Remaining backend limitations

Evidence-driven only. Each is a measured observation, not a projection.

1. **One wrong non-null personal name from OCR**, at high confidence, contained
   only by the evidence policy. Section I.
2. **Recall 0.471.** Seventeen required fields unresolved across seven
   documents, dominated by table and layout structure.
3. **No table understanding.** A course table with seven distinct grade-point
   figures is read as seven conflicting candidates. The pipeline abstains, which
   is safe, but cannot identify the overall figure. The earlier behaviour that
   appeared to solve this was reading-order luck, not extraction.
4. **Layout loss on header-band and multi-line text.** University and department
   labels frequently sit away from their values in these scans.
5. **Row grouping across distant table cells.** Label/value pairs in separate
   cells with a large horizontal gap are not paired.
6. **Three supported types unexercised** by real input: graduation, career and
   national tax payment certificates.
7. **No born-digital input.** The embedded-PDF-text ingestion and evidence route
   is completely unexercised by this corpus.
8. **No real multi-page document.** Multi-page architecture is validated only
   with mechanical fixtures.
9. **Review load is structurally high.** On scanned input no document can reach
   `READY` without human confirmation of every OCR-sourced value. Correct, but
   operationally expensive.
10. **Comparison normalisation differs between validation scopes.**
    `security_regression.md`.

## AB. P1 priorities

Ranked by impact, frequency, safety and workflow importance. **None of these were
implemented.**

| Rank | Problem | Impact | Frequency | Safety | Rationale |
|---|---|---|---|---|---|
| 1 | Reduce wrong non-null values from OCR, especially personal names | high | moderate | **high** | The only wrong value produced. Every additional document adds exposure. Needs spatial disambiguation quality, not a confidence tweak. |
| 2 | Table structure understanding | high | **high** | moderate | Blocks GPA, and will block any table-shaped field. The single largest recall loss. |
| 3 | Layout reconstruction for header-band and multi-line text | high | **high** | low | Blocks university, department and similar fields on both enrollment and transcript. |
| 4 | Row grouping across distant table cells | moderate | high | low | Feeds both 2 and 3. |
| 5 | Section semantics: distinguish totals from per-block rows | moderate | moderate | moderate | Would let GPA resolve on evidence rather than reading order. |
| 6 | Unify comparison normalisation across validation scopes | low | low | low | Avoids future surprising mismatches; today it fails safe. |
| 7 | Exercise and harden the born-digital PDF route | moderate | unknown | moderate | Entire ingestion path is untested against real input. |

Explicitly **not** started: no new table engine, no new layout architecture, no
VLM or LLM extraction, no cloud OCR, no global deskew pipeline, no admin
configuration UI.

## AC. Commit

| Field | Value |
|---|---|
| Hash | `14de9a38e1a60e50547a52ab0285d905397bf4af` |
| Short | `14de9a3` |
| Message | `Stabilize backend document processing and verification` |
| Author | `KHABIBILLO <khabibillionaire@gmail.com>` |
| Timestamp | 2026-10-03 01:34:02 +0900 |
| Contents | 33 files changed, 2656 insertions, 57 deletions |

One commit. No history rewrite, no amend of prior work, no backdating, no empty
commit. Files were staged explicitly by path; `git add .` was not used.

Staged set, by category:

- **P0_PRODUCTION** — `.gitignore`, and nine modules under
  `apps/api/app/`: `core/domain.py`, `core/logging.py`,
  `document_intelligence/extraction/base.py`,
  `document_intelligence/ocr/providers.py`,
  `document_intelligence/ocr/worker.py`,
  `document_intelligence/validation/submission.py`,
  `services/requirements.py`, `services/reviews.py`,
  `services/storage/local.py`.
- **P0_TEST** — `tests/test_p0_backend_stabilization.py` (new, 13 tests) and
  `tests/test_astra_ingestion.py`.
- **P0_SAFE_REPORT** — 22 files under `evaluation/p0_backend/`.

Deliberately **not** staged, verified by explicit check:

| Path | Category | Reason |
|---|---|---|
| `evaluation/backend_round2/work/` | PRIVATE | real ground truth and raw OCR; gitignored |
| `evaluation/private_runtime/` | PRIVATE | this run's raw output; gitignored |
| `evaluation/real_backend_validation/` | PREEXISTING, PII-bearing | earlier session's evidence; contains real identifiers; not audited to a safe standard here |
| `evaluation/astra_backend/` | PREEXISTING | earlier session's evidence; out of scope |
| `evaluation/backend_round2/` (rest) | PREEXISTING, PII-bearing | the local evaluation harness and its records; two of its JSON/MD files contain real institution names and dates |
| `evaluation/results/round2_*` | PREEXISTING | earlier session's outputs |
| `temp` | UNRELATED | a Mach-O binary present before this task |
| `txt.txt` | UNRELATED | the task brief, not a project file |

A programmatic scan compared every private ground-truth value and every source
filename against all staged content and reported **zero matches**. One real
institution name that an earlier session had copied into the new test file was
found by that scan and replaced with an obviously fictional name before staging.

Note that the evaluation harness itself is **not** committed. It lives under
`evaluation/backend_round2/` alongside records that contain real values, so
committing part of that directory would have created an inconsistent partial
tree. The harness is versioned by the SHA-256 hashes recorded in
`final_validation_start.md`, so the exact evaluator used here remains
identifiable.

## AD. Push

| Field | Value |
|---|---|
| Remote | `git@github-khabibro:khabibro/ADVS.git` |
| Branch | `main` |
| Authenticated account | `khabibro` |
| Result | `f641fee..14de9a3  main -> main` |
| Force | no |

`git fetch origin` was run first and confirmed `origin/main` had not diverged:
the branch was linear and ahead by exactly one commit. No rebase, no merge, no
force push.

Post-push verification: `HEAD` and `origin/main` are both
`14de9a38e1a60e50547a52ab0285d905397bf4af`, and the working tree is clean with
respect to the branch.

## AE. Final worktree

Left uncommitted by design:

| Path | Reason |
|---|---|
| `evaluation/backend_round2/work/` | real ground truth and raw OCR; gitignored by policy |
| `evaluation/private_runtime/` | raw run output for this validation; gitignored by policy |
| `evaluation/real_backend_validation/`, `evaluation/astra_backend/`, `evaluation/results/round2_*` | pre-existing untracked evidence from earlier sessions, outside this task's scope, **not audited for private data and therefore not committed** |
| `temp` | an unrelated Mach-O binary present before this task |
| `txt.txt` | the task brief, not a project file |
| the git worktree used for the PRE-P0 measurement | removed after use |

## AF. Claim boundaries

What this evidence **does** support:

- On seven specific scanned Korean administrative documents, the current backend
  ingests all seven, classifies all seven correctly, and produces no fabricated
  fields.
- False READY is 0, down from 3 at the PRE-P0 reference, measured over the same
  files with the same gold and the same scorer.
- Field recall on this corpus is 0.471 and field precision 0.941.
- Upload, multi-page, timeout recovery, concurrency, review closure, logging and
  comparison semantics behave as described, against real PaddleOCR and a live
  HTTP server.
- All backend and frontend quality gates pass.

What this evidence **does not** support, and is not claimed:

- **Not** production-ready Korean document intelligence.
- **Not** high real-world accuracy. Recall is below one half and one required
  field is wrong.
- **Not** robust table extraction. Course-table documents are not handled.
- **Not** broad administrative-document coverage. Three supported types, born-digital
  PDFs and real multi-page documents are all unexercised.
- **Not** a validated complete business pack.
- **Not** evidence that `READY` is reachable in practice; on scanned input it is
  not, by design.

`READY` means no obvious configured issue was detected. It does not mean the
submission is accepted, and in this configuration a scanned document cannot
reach it without human confirmation.