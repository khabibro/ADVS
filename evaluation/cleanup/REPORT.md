# ADVS Cleanup and Architecture Documentation — Final Report

Branch `docs/cleanup-architecture`, 6 commits ahead of `main`
(`6f7605f`, identical to `origin/main`), not pushed, not merged. No
production code was changed anywhere in this task.

```
4dc71b2  Protect P2.2 adjudication scripts from accidental commit
31d4c5f  Archive superseded planning docs
906d034  Point A5 check at the in-repo test-variant location
f1d949f  Organize evaluation/ with a phase-history map and gold-version explainer
e369555  Add Part A1 cleanup inventory
e72eced  Add verified architecture docs, glossary, and recommendations
```

## What was found and approved (Part A1 → `evaluation/cleanup/cleanup_plan.md`)

Six open points were put to you after the read-only inventory; all six were
approved as recommended:

1. Privacy: `evaluation/p2_2_targeted_improvement/` added to `.gitignore` —
   one of its scripts hardcoded a transcribed real-document value with no
   protection against an accidental `git add -A`.
2. Phase A's own untracked deliverables (`evaluation/phase_a_baseline/`, 7
   of 8 files) left as-is — out of this task's scope, still untracked on
   `main`, flagged for a separate decision.
3. Stray `apps/api/.venv` (555 MB, Python 3.14, unreferenced) deleted
   outright rather than archived.
4. Empty, unreferenced `evaluation/submissions/` directory removed.
5. Dormant `extraction/structural.py` left untouched (production code,
   out of scope either way) — documented instead, in `docs/ARCHITECTURE.md`
   §10 and `docs/RECOMMENDATIONS.md` item 6.
6. Four `__pycache__/` directories and one `.DS_Store` deleted outright.

One thing outside the repo was also found and fixed mid-task, with your
separate approval: `~/Desktop/ADVS_test_variants/` was a stale duplicate of
the test-variant set already moved into the repo on `phase-b/safety-fixes`
(commit `ae51680`) — hash-verified byte-identical to `manifest.json` in
both locations, then deleted.

## Part A2 — what actually moved/changed

- Deleted: `apps/api/.venv`, 4 `__pycache__/` dirs, 1 `.DS_Store`, the
  empty `evaluation/submissions/` directory.
- `.gitignore`: added `evaluation/p2_2_targeted_improvement/`.
- `docs/planning/ROADMAP.md` and `DEVELOPMENT_PLAN.md` → moved to
  `docs/archive/` with an explanatory note prepended to each (their phase
  numbering predates how the project actually proceeded); one stale
  cross-reference in `docs/archive/PROJECT_OVERVIEW.md` corrected;
  `docs/DOCUMENTATION_INDEX.md` updated to match.
- Nothing tracked was `git rm`'d — the inventory found no tracked file
  that qualified for removal; everything tracked under `evaluation/` is
  already organized phase history (see Part B).
- One fix outside this task's original scope, made necessary by the
  Desktop duplicate's removal: `evaluation/phase_a_baseline/a5_checks.py`
  hardcoded the now-deleted Desktop path as its source; repointed to the
  in-repo location and re-verified it reproduces `A5_checks.json` exactly.

## Part A3 — verification

Backend: `ruff check` clean, `mypy --explicit-package-bases app` clean
(63 source files), `pytest` 368/368 passing. Frontend: `pnpm lint`,
`pnpm typecheck`, `pnpm build` (web + admin) all clean. Phase A scorer
reproducibility: both `score_b0_v2_v3.py` and `a5_checks.py` re-run after
every change in this task and diffed byte-for-byte against the
pre-existing `B0_score_v2_vs_v3.json`/`A5_checks.json` — identical every
time, including after the final Part C commit.

One unexplained anomaly, caught and fixed, not traced to a specific
command in this session: `sample_data/README.md` and
`sample_data/fixtures/graduation_certificate.txt` were found deleted from
the working tree partway through this task, with no corresponding command
in this session's history that targeted them. Restored immediately via
`git checkout -- sample_data/` (both files are small and fully tracked, so
this was a clean, lossless recovery). Flagging this rather than silently
moving on, since the cause wasn't identified.

## Part B — `evaluation/README.md`

Added a phase-history folder map (every top-level directory under
`evaluation/` that isn't part of the wired `make eval-*` toolkit, with what
phase produced it), and a "Gold label versions" section that separates two
previously-conflated systems: the synthetic/recreated schema-v1.1 gold
`make eval-*` scores against, and the real-document round-2
`ground_truth` v1→v2→v3 adjudication history (REAL-001..007). Also
corrected a stale claim: `results/` and `reports/` were described as
"gitignored except `.gitkeep`" but have no such `.gitignore` entry and are
fully tracked (verified via `git ls-files`).

## Part C — `docs/`

- **`docs/ARCHITECTURE.md`** (new, canonical): system context, component
  map, pipeline sequence diagram, ERD, decision-rules diagram,
  configuration diagram, the full document-type/field table, frontend
  architecture, a dormant-code section, and a known-limitations table
  cross-referenced to the independent audit's F-001..F-020 findings with
  each one's fix status (on `main` vs. the unmerged `phase-b/safety-fixes`
  branch) — plus an extension guide for adding a document type, a
  validation rule, or a workflow.
- **`docs/GLOSSARY.md`** (new): every domain/process term used across the
  code and the evaluation reports, cross-linked to where each is defined.
- **`docs/RECOMMENDATIONS.md`** (new): 13 proposed next steps, ordered by
  severity, each citing its evidence — **nothing in it has been
  implemented**.
- **`docs/architecture/ARCHITECTURE.md`**: kept (its evidence-conventions
  detail isn't repeated in the new file), with a pointer to the new file
  as canonical.
- **`docs/DOCUMENTATION_INDEX.md`**, **`README.md`**: updated to point at
  the new files and to correct the stale "CURRENT PHASE" line.
- **`evaluation/cleanup/check_docs.py`** (new): mechanically re-verifies
  every file/directory reference, every `DocumentType`/`RuleType`/
  `OverallStatus` member, every required/optional field, every ERD entity
  against `app/models/entities.py`, every cited `make` target, and every
  cited F-00x finding, against the actual code — not a one-time check,
  meant to be re-run after future changes (see its own docstring and
  `docs/RECOMMENDATIONS.md` item 12). Currently passes clean.

## What was not done (explicitly out of scope)

- Phase A's own untracked deliverables were not committed.
- `phase-b/safety-fixes` was not merged, reviewed, or touched.
- `extraction/structural.py` was not committed, moved, or deleted —
  documented as-is only, since the task forbids touching production code.
- `apps/admin` was not given tests, `OCR_PROVIDER=mock` was not guarded,
  no authentication was added, and no business-number checksum was added
  — all tracked as proposals in `docs/RECOMMENDATIONS.md`, none
  implemented.

## Not pushed, not merged, no further phase started.
