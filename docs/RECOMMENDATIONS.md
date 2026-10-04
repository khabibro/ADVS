# Recommendations

Proposed next steps only — **nothing in this file has been implemented**.
Each item cites where the underlying evidence lives so it can be checked
independently rather than taken on faith. Ordered roughly by severity/risk,
not by effort.

## Safety (S0/S1 findings, `evaluation/system_audit/ADVS_system_audit_report.md`)

1. **Merge `phase-b/safety-fixes` after review**, or re-derive its fixes on
   `main` if the branch itself isn't what should land. It already fixes
   F-001 (partial `REQUIRED_FIELD` checklist disabling the missing-field
   net), F-002 (company-name notation), F-003 (look-alike classification),
   and the validity-reference-date instability Phase A measured directly —
   each with failing-then-passing tests and a measured before/after
   (`evaluation/phase_b/PHASE_B_REPORT.md`). This is the single highest-
   value recommendation in this file: real, already-fixed safety defects
   are sitting unmerged.
2. **Add authentication/authorization** (F-007). Every endpoint is
   currently open; `User`/`owner_id` exist in the schema but nothing
   creates, authenticates, or distinguishes between users. Pair with a
   decision on what "admin" vs. "applicant" should actually be allowed to
   do, since `apps/admin` currently has no access control to design against.
3. **Add a checksum validation for Korean business registration numbers**
   (F-004) — the 10-digit check-digit algorithm is public and would catch
   transcription/OCR errors the current string-equality check cannot.

## Correctness/robustness (S2)

4. **Fix `render_dpi` metadata to report actual per-page DPI**, not the
   configured value, when a page is downscaled (F-005) — currently
   misleading for debugging OCR-quality issues on large pages.
5. **Re-check the test-count claim precision** (F-020) — not re-verified in
   this cleanup pass; worth a fresh look alongside whatever test suite
   exists after `phase-b/safety-fixes` merges (408 tests at that branch's
   last commit vs. 368 on `main` today).

## Process/hygiene (S3, and this cleanup's own findings)

6. **Decide the fate of `extraction/structural.py` and `layout/`**
   (§10, `docs/ARCHITECTURE.md`). Both are real, tested, dormant code.
   Either commit them as documented "available but not wired" extension
   points, or remove them — leaving them untracked indefinitely (their
   current state before this task) risks silent loss.
7. **Finish committing Phase A's own deliverables** —
   `evaluation/phase_a_baseline/` has 7 of 8 files still untracked on
   `main`, including `BASELINE_B0_pre_safety.md`, which every later phase's
   precondition check reads. This cleanup task deliberately left that
   decision to the project owner (out of this task's stated scope) —
   see `evaluation/cleanup/cleanup_plan.md` finding 2.
8. **Add an environment-aware guard on `OCR_PROVIDER=mock`** (F-006) so a
   misconfigured non-test environment can't silently run on fake OCR output.
9. **Give `apps/admin` a test suite** (F-008) before treating it as more
   than a structural shell — it currently has zero tests.
10. **Replace or clearly scope-down the "security:audit" script's claim**
    (F-009) — it's a narrow static check, and calling it a security audit
    overstates what it verifies.
11. **Re-run `make eval-paddle` / the real-corpus round-2 scorer once
    `~/Desktop/Samples/` (or an equivalent source folder) is available
    again** — this cleanup task's Part A3 and Phase B's own B1 measurement
    both found the real-document source folder missing on this machine,
    forcing an inference-not-measurement verdict for several acceptance
    criteria. A fresh run would upgrade those from "assessed by code-path
    analysis" to "measured."

## Documentation upkeep

12. **Run `evaluation/cleanup/check_docs.py` after any change to
    `app/core/domain.py`, `models/entities.py`, or `api/v1/routes.py`** —
    those three files are what `docs/ARCHITECTURE.md`'s tables, ERD, and
    API list are generated from by hand; the script catches drift
    mechanically rather than relying on someone remembering to update prose.
13. **When `phase-b/safety-fixes` merges**, update
    `docs/ARCHITECTURE.md` §11's "Status on `main`" column and
    `docs/GLOSSARY.md`'s look-alike-document entry — both currently say
    "unmerged branch," which becomes stale the moment that's no longer true.
