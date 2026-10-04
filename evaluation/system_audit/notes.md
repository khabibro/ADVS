# ADVS System Audit — Working Notes

Started: 2026-10-04. Auditor: independent (this session). Read-only on
production; no git writes; scratch work confined to this directory.

Confirmed starting state: branch `main`, HEAD `48e3824a780e3c051cba2d2eb1838851db1fcf1e`,
`git status --porcelain` matches the state recorded in the P2.1 adjudication
phase immediately prior (one modified tracked file, several untracked
evaluation/test directories). No discrepancy.

## Plan

1. [ ] 4.1 Repo state: map layout, dependency versions, check history for
   committed private data.
2. [ ] 4.2 Requirements traceability matrix — build iteratively while
   reading extractors/validators per document type.
3. [ ] 4.3 Pipeline walk-through, stage by stage, real code path only.
   - DPI discrepancy (REAL-001 288 vs 108)
   - structural layer reachability
   - MockOCRProvider selectability
4. [ ] 4.4 Classification + extraction correctness, hardcoding grep,
   overfitting assessment via git log/blame.
5. [ ] 4.5 Safety invariants — read code, then write small probes in this
   directory calling real functions directly (no prod file edits).
6. [ ] 4.6 Evaluation methodology — find scorer, try to reproduce headline
   numbers from repo scripts.
7. [ ] 4.7 Run quality gates (backend tests, frontend tests, lint, types,
   build, migrations). Record exact commands + pass/fail counts.
8. [ ] 4.8 Architecture / robustness / security / privacy.
9. [ ] 4.9 Frontend correctness.
10. [ ] 4.10 Fitness for target (demo/real-doc/production readiness).
11. [ ] Write final report `ADVS_system_audit_report.md`.

## Running findings log (ID, severity, one-liner) — filled in as found

(see bottom of file for running list)
