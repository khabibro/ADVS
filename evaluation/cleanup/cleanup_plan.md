# ADVS Cleanup Plan — Part A1 Inventory (read-only)

Branch: `docs/cleanup-architecture`, created from `main` at commit `6f7605f`
(verified identical to `origin/main`, 0 commits ahead/behind). No files have
been moved, deleted, or committed by this document — this is the inventory
only, per the task's required stop-for-approval gate. Phase B's work
(`phase-b/safety-fixes`, 6 commits, not merged) is untouched and out of
scope for this task.

One mid-task correction already made, outside the repo (not part of this
plan, reported for transparency): `~/Desktop/ADVS_test_variants/` was found
to be a stale duplicate of the test-variant set already moved into the repo
on `phase-b/safety-fixes` (commit `ae51680`) — the original "mv, not copy"
had left the source behind. Hash-verified byte-identical against
`manifest.json` in both locations (0 missing/mismatched in each), then
deleted with your approval. Nothing in the repo was touched by this.

## 0. Top findings (read this first)

1. **Privacy-relevant: untracked file with inline transcribed real-document
   values, no protective `.gitignore` rule.**
   `evaluation/p2_2_targeted_improvement/adjudicate_gold.py` hardcodes a
   `DECISIONS` list with transcribed field values from real documents
   (e.g., a GPA tied to `REAL-003`) directly in the `.py` source — not in a
   data file under `private_runtime/`. It is untracked today (never
   `git add`ed), but nothing currently stops a future `git add -A` from
   committing it. The script's own `RUNTIME` constant points at
   `evaluation/private_runtime/p2_2/` (already gitignored) for its
   *outputs*, but the script itself, containing the *inputs*, sits
   unprotected one level up. **Recommendation: add
   `evaluation/p2_2_targeted_improvement/` to `.gitignore`** (cheapest,
   non-destructive fix, preserves the path so existing citations to it in
   `A2_verification.md`, `BASELINE_B0_pre_safety.md`, and
   `privacy_scan_before_commit.md` keep resolving) rather than moving it.
   Needs your sign-off since it's a `.gitignore` edit, not a pure read.
   The other 7 scripts in that directory were checked for the same pattern
   (regex for RRN-shaped and business-number-shaped strings) and found
   clean; recommend the directory-level gitignore anyway since they're all
   part of the same untracked, uncommitted batch.

2. **Valuable Phase A work exists only in the working tree, never
   committed to `main`.** Of `evaluation/phase_a_baseline/`'s 8 files, only
   `A1_decision_memo.md` is tracked. `BASELINE_B0_pre_safety.md` (the file
   every later phase's precondition check reads), `A2_verification.md`,
   `A3_manifest.md`, `A5_checks.json`/`a5_checks.py`, and
   `B0_score_v2_vs_v3.json`/`score_b0_v2_v3.py` are all untracked. This
   isn't "unused scratch" — it's load-bearing (Phase B's whole before/after
   measurement depends on `BASELINE_B0_pre_safety.md`), it's safe to commit
   (safe IDs only, no real values — same privacy scan already covered
   this), and it predates and is independent of this cleanup task. **This
   plan does not commit it** (out of this task's stated scope, and mixing
   Phase A bookkeeping into the docs/cleanup branch would blur
   provenance) — flagging it so you can decide separately whether to
   finish committing Phase A on `main` before or after this task.

3. **Everything else under `evaluation/` is already tracked and already
   organized by phase.** The actual untracked "clutter" is narrow: 4
   `__pycache__/` dirs, 1 `.DS_Store`, and 2 stray Python virtualenvs at
   `apps/api/.venv` (Python 3.14, 555 MB) and `apps/api/.venv312` (Python
   3.12, 1.0 GB — this one is the real one; `Makefile`'s `API_VENV ?=
   .venv312`). Both venvs are already gitignored (zero git risk either
   way) and regenerable via `pip install -e ".[dev,paddle]"` — `.venv` is
   not referenced by anything and is a pure duplicate-engine leftover.

4. **One documentation fact is already stale.** `evaluation/README.md`
   states `evaluation/results/` and `evaluation/reports/` are
   "gitignore-exempt only for `.gitkeep`," but the current `.gitignore` has
   no entry for either path at all — both directories are fully tracked,
   unconditionally (44 and 7 files respectively, all committed). Minor,
   but it's exactly the kind of claim Part C's `check_docs.py` is meant to
   catch, so flagging it now too.

5. **No orphaned top-level files remain at the repo root.** `temp` and
   `txt.txt` (named explicitly in the task prompt) no longer exist —
   already cleaned up in an earlier session, confirmed by direct `find`.
   `extraction/structural.py` does exist (as
   `apps/api/app/document_intelligence/extraction/structural.py`, 261
   lines, untracked) — see §3.

## 1. Repo root

| Item | Tracked? | Size | What it is | Classification |
|---|---|---|---|---|
| `apps/`, `packages/`, `scripts/`, `infra/`, `tests/e2e/` | tracked | 2.2G (mostly `node_modules`/`.venv*` inside) | source monorepo | KEEP |
| `docs/` | tracked | 108K | project docs | KEEP — see §4 |
| `sample_data/` | tracked | 8K | 2 tiny fixture files | KEEP — see §3 |
| `evaluation/` | tracked (+ untracked subset) | 84M | eval toolkit + phase history | KEEP — see §2 |
| `storage/paddleocr-cache/` | gitignored | 25M | PaddleOCR model cache | KEEP (operational, regenerable, correctly ignored) |
| `node_modules/`, `.turbo/`, `.pnpm-store/` | gitignored | 1.4G+764M+small | JS build caches | KEEP as-is, not a cleanup target |
| `apps/api/.venv` | gitignored | 555M | stray Python 3.14 venv, not referenced anywhere | **DELETE (needs your OK — see finding 3)** |
| `apps/api/.venv312` | gitignored | 1.0G | the real venv (`Makefile` default) | KEEP |
| `temp`, `txt.txt` | — | — | named in the task prompt | **already gone**, no action needed |
| `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `LICENSE_NOTE.md`, `Makefile`, `docker-compose.yml`, `turbo.json`, `pnpm-workspace.yaml`, `package.json`, `.env.example`, `.dockerignore`, `.gitignore`, `.github/`, `.agents/` | tracked | small | root config/docs | KEEP — `README.md` content assessed in §4 |
| `.ruff_cache/` | gitignored | 20K | lint cache | KEEP as-is |

## 2. `evaluation/` — by top-level directory

Legend: *Wired* = referenced by a `make eval-*`/`make baseline*` target in
`Makefile` and documented in `evaluation/README.md`. *Phase history* =
tracked, self-contained `.md` report(s) from a completed investigation
phase of this capstone project, not wired to any command but part of the
project's evidentiary record. None of the phase-history directories are
referenced from `Makefile`, `docs/`, `README.md`, or `evaluation/README.md`
— that absence is itself finding-worthy (see Part B: they need an index).

| Directory | Tracked/total files | Last touched | Role | Classification |
|---|---|---|---|---|
| `datasets/` | 276/578* | 2026-09-15 | Wired — synthetic/recreated/real benchmark corpus | KEEP |
| `gold/` | 138/138 | 2026-09-15 | Wired — gold labels for the above | KEEP |
| `results/` | 44/44 | 2026-10-04 | Wired — per-run JSON/CSV output | KEEP (doc claim about gitignore is stale, see finding 4) |
| `reports/` | 7/7 | 2026-09-15 | Wired — baseline/final Markdown reports | KEEP |
| `baselines/` | 4/4 | 2026-09-15 | Wired — Phase 0 baseline snapshots | KEEP |
| `sources/` | 1/1 | 2026-09-15 | Wired — `source_registry.json` provenance | KEEP |
| `cache/` | 1/1 (`.gitkeep` only) | 2026-09-15 | Wired — reserved, empty | KEEP |
| `submissions/` | 0/0 | — | empty directory, no files at all | **UNSURE — remove the empty dir, or is something meant to land here?** |
| `p0_backend/` | 21/21 | 2026-10-03 | Phase history — P0 backend validation (17 reports) | KEEP |
| `p1_layout/` | 20/22 | 2026-10-04 | Phase history — P1 structural layout layer | KEEP (2 untracked `__pycache__` files — DELETE those only) |
| `p2_1_ocr_diagnosis/` | 19/20 | 2026-10-04 | Phase history — P2.1 OCR diagnosis | KEEP (1 untracked `__pycache__` file — DELETE) |
| `p2_ocr/` | 22/22 | 2026-10-04 | Phase history — P2 OCR work | KEEP |
| `p2_2_targeted_improvement/` | 0/10 | — (never committed) | P2.2 targeted-improvement scripts, incl. the file in finding 1 | **KEEP the scripts, but add directory to `.gitignore` first — see finding 1.** Also contains 2 `__pycache__` files — DELETE those regardless. |
| `astra_backend/` | 17/17 | 2026-10-04 | Phase history — architecture/research review | KEEP |
| `real_backend_validation/` | 17/17 | 2026-10-04 | Phase history — backend readiness validation | KEEP |
| `backend_audit/` | 9/17 | 2026-09-29 | Phase history — OCR/DPI audit | KEEP tracked reports. 8 untracked files are all under `backend_audit/work/` (gitignored by rule, contains rendered pages from a real scan) — already correctly excluded from git, **no action** |
| `backend_round2/` | 19/37 | 2026-10-04 | Phase history — real-corpus round 2 (this session's P2.1 adjudication) | KEEP tracked reports/scripts. 18 untracked files are all under `backend_round2/work/` (gitignored by rule — ground-truth v1/v2/v3, private diagnostics) — correctly excluded, **no action** |
| `phase5/`, `phase6/`, `phase7/` | 5/5, 2/2, 4/4 | 2026-09-22/22/28 | Phase history — later numbered phases (frontend-adjacent, per filenames) | KEEP |
| `phase8/` | 1/1 | 2026-09-29 | Phase history — frontend audit baseline | KEEP |
| `phase_a_baseline/` | 1/8 | 2026-10-04 | **This session's Phase A** — see finding 2 | KEEP; commit status is an open question, not a cleanup action |
| `system_audit/` | 4/4 | 2026-10-04 | **This session's independent full-system audit** | KEEP |
| `private_runtime/` | gitignored, 23M | — | per-run private evaluation data (real names, IDs) | KEEP, do not move anywhere — working as designed |

\* The 302-file gap in `datasets/` is almost entirely the Phase B
test-variant binaries (299 files, gitignored by rule on `phase-b/safety-fixes`
but that `.gitignore` entry is not on `main`/this branch, so they show as
untracked here) plus `real/inbox/real_0001_enrollment.pdf` (a real document,
correctly gitignored by the `evaluation/datasets/real/**` rule) and one
stray `test_variants/.DS_Store`. None of this is a cleanup action on this
branch — the test-variant binaries belong to the unmerged Phase B branch,
not to this one, and the real document and private-runtime data are
intentionally untracked by design. **DELETE** only the `.DS_Store`.

## 3. `sample_data/` and the two named loose files

- `sample_data/README.md` + `sample_data/fixtures/graduation_certificate.txt`
  — tiny (141B + 148B), tracked, referenced as the project's minimal fixture
  example. KEEP.
- `apps/api/app/document_intelligence/extraction/structural.py` — 261
  lines, untracked, dated Oct 3. Docstring says it implements additive
  "structural candidate" extraction helpers (`header_value_candidate`,
  `section_scoped_candidate`), explicitly describes a `role_candidate`
  that "was implemented, measured, and disabled." Grep confirms **no other
  module imports it** — it is dormant/unwired code, consistent with the
  existing `docs/architecture/ARCHITECTURE.md`'s "Known limitations"
  practice of calling out dormant modules (it already does this for the
  P1 layout layer). **UNSURE**: this is production code, which this task
  is not allowed to change — but should it be (a) left as untracked dead
  code, (b) committed as dormant/documented-as-such, or (c) deleted as
  abandoned? Needs your call; this plan takes no action on it either way
  since the task's hard constraint forbids touching production code.

## 4. Documentation currency — `docs/` and root `README.md`

`docs/` is already fairly organized (`architecture/`, `domains/`,
`operations/`, `planning/`, `security/`, `archive/`, plus
`DOCUMENTATION_INDEX.md`) — this is **not a flat, undocumented mess**; the
task's planned `docs/ARCHITECTURE.md` / `GLOSSARY.md` / `RECOMMENDATIONS.md`
would be *new, differently-scoped* files (root of `docs/`, not
`docs/architecture/`), so Part C needs to either supersede or explicitly
cross-link the existing `architecture/` subfolder rather than silently
duplicating it.

| File | Last touched | Assessment |
|---|---|---|
| `docs/architecture/ARCHITECTURE.md` | 2026-09-28 | **Current** — spot-checked against the pipeline code in this session's earlier audit; accurate to `main`. Missing the dormant P1 layout module and `structural.py` in its "Known limitations," and necessarily silent on unmerged Phase A/B work (correctly out of scope for a doc describing `main`). |
| `docs/architecture/DATA_MODEL.md`, `API_DESIGN.md` | 2026-09-28, 2026-09-22 | Current, not independently re-verified line-by-line in this pass (Part C will do that against the actual schema/routes) |
| `docs/domains/*.md` (7 files) | 2026-09-15 to 2026-09-22 | Current — most recently touched alongside the matching code changes |
| `docs/operations/*.md` (4 files) | 2026-09-12 to 2026-09-22 | Current |
| `docs/security/document-privacy.md` | 2026-09-15 | Current, brief |
| `docs/planning/ROADMAP.md`, `DEVELOPMENT_PLAN.md` | 2026-09-12 | **Outdated** — pre-dates Phase 2/P2.x/P0/Phase A/B entirely; describes earlier planning, not where the project actually is now |
| `docs/archive/*.md` (3 files) | 2026-09-05/15 | Already correctly filed as archive — no action needed, already in the right place |
| `docs/DOCUMENTATION_INDEX.md` | 2026-09-15 | Current as an index of the above, will need one new line added for Part C's new files |
| `evaluation/README.md` | 2026-09-15 | **Mostly current, one stale claim** — see finding 4 |
| root `README.md` | 2026-09-20 | **Current** — matches `Makefile` targets, Python version pin, and monorepo layout checked in this pass; says "CURRENT PHASE: Phase 2 mentor-defined document domain," which is now behind reality (P0, Phase A, Phase B have since happened on other branches) but that's a staleness of *phase label*, not of the technical content, and this task's Part C is exactly where that gets brought current |

## 5. Decisions needed from you before Part A2 touches anything

1. Finding 1 (privacy): add `evaluation/p2_2_targeted_improvement/` to
   `.gitignore`? (Recommended: yes.)
2. Finding 2 (Phase A untracked deliverables): commit them now as part of
   this task, commit them separately yourself, or leave as-is for now?
   (This plan defaults to **leave as-is** unless you say otherwise — out of
   scope.)
3. `apps/api/.venv` (555 MB, stray Python 3.14 venv): delete outright, or
   archive to `~/ADVS_archive_<date>/` per the task's general
   archive-don't-delete rule? (Recommended: delete outright — it's
   gitignored, regenerable, and referenced nowhere; archiving 555 MB of a
   duplicate virtualenv has no evidentiary value.)
4. `evaluation/submissions/` (empty dir, untracked, no files, not
   referenced): delete the empty directory, or is it a placeholder for
   something not yet built?
5. `apps/api/app/document_intelligence/extraction/structural.py` (dormant
   production code, untracked): no action is being proposed either way
   (task forbids touching production code) — just flagging it as a Part C
   "known limitations / dormant code" documentation item.
6. The 4 `__pycache__/` dirs and 1 `.DS_Store` (finding 3/§2 table): these
   are proposed for straight deletion (regenerable bytecode cache /
   OS metadata, zero evidentiary value) rather than archiving — confirm
   that's fine, or should literally everything untracked go through the
   archive folder per the task's general rule?

Nothing above has been moved, deleted, or committed. Awaiting your go-ahead
on these six points before Part A2.
