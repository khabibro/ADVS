# OCR-only cleanup report

Date: 2026-10-11. Commit `e5b2569` ("Remove VLM experiment references; traditional OCR only"), tag `midterm-demo-v3.1`. (After the 2026-10-11 history rewrite the commit and tag IDs are `4f936e4` / `midterm-demo-v3.1`; the trees are unchanged.)

## Decision
The owner decided that the MVP uses traditional OCR only: OCR → deterministic field extraction and normalisation → validation and cross-document checks → safe submission decision. The second-reader experiment run in isolation during Phase G is removed from the active project. It stays available only on the branch `research/vlm-poc` (not merged into `main`).

## What changed (16 files, +97 / −196)
- Deleted the second-reader stage script `evaluation/phase_g/scripts/final_judgement_vlm.sh`; dropped that stage from `final_judgement.sh`.
- Rewrote to the OCR-only scope: `evaluation/phase_f/APPROACH_EVALUATION.md`, `EVALUATION_PROTOCOL.md`, `TECHNICAL_AUDIT.md`, `evaluation/phase_g/PHASE_G_REPORT.md`, `evaluation/README.md`, `docs/planning/ROADMAP.md`, `docs/midterm/ROADMAP.md`, the November and December report templates, `docs/DOCUMENTATION_INDEX.md`.
- Documented the retained seven-step pipeline in `docs/architecture/ARCHITECTURE.md`.
- Midterm deck and PDF (`docs/midterm/ADVS_midterm.*`): pipeline slide shows the retained pipeline; appendix, roadmap, completion criteria and Q&A no longer mention a second recognition model; `docs/midterm/slides_sources.md` updated.
- No application code, dependency or test changed (none referenced the experiment).

## Test results after the cleanup (2026-10-11)
- Backend 613 tests and web 108 unit tests pass.
- OCR evaluation replay (frozen scorer v2, sha256 `49674a9c…2594`): zero differences against the preserved baseline; dev gates exit 0. False 제출 가능 0 on dev, hold-out 1 and 2; injected-error suites 0 / 1,354, 0 / 1,532, 1 / 1,523 (the owner-accepted H14 case) false READY.
- Demo rehearsal: ALL PASS. Playwright: 15 passed, 7 skipped (they need the mentor's real documents, deliberately not used).
- Manipulated PDFs: suite and API pipeline runs exit 0 (0 / 705 missed; 12 / 12 held).

## Remaining references (intentional or unrelated)
- `evaluation/phase_g/PHASE_G_REPORT.md` §"OCR-only": one paragraph stating the experiment was removed.
- `evaluation/phase_g/final/session_log.txt` line 1: the historical "frozen VLM config" hash, kept because the session log is an audit record of hold-out 3.
- `evaluation/reports/ADVS_system_audit_report.md` (about line 833): a sentence saying the audit's recommendations do not propose adding an LLM/VLM.
- `pnpm-lock.yaml`: "vlm" occurs only inside integrity hashes (unrelated).
- `docs/planning/ADVS_original_plan.docx` (the original 수행계획 script) mentions LLMs as originally planned; it is kept as a historical record and not used in the deck.
- The branch `research/vlm-poc` and its tag on GitHub, untouched.
