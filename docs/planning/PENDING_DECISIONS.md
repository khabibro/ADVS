# Decisions recorded 2026-10-31 (owner), to be implemented later

Source: the admin/web analysis (`ADMIN_WEB_ANALYSIS.md`, `ADMIN_WEB_DESIGN.md`, kept as drafts). Nothing here is implemented yet; each phase needs all gates and the owner's OK before it starts. The merge of `research/real-docs` (with the fixes) waits for the owner's approval of the final report.

## Decisions
1. Checklist version 1 does **not** contain the fixed `issue_date <= 2026-12-31` rule (it would fail every student submission from 2027-01-01; the age rule already bounds the date).
2. **Staff-only confirmation.** Applicants see "담당자 확인 중" and can never move a status to 제출 가능 (no self-confirmation of OCR values).
3. Applicants get a **per-submission link**; the admin app is internal-only for now; authentication is still required.
4. "학번 on at least one document" becomes a configurable rule option ("any document" or "document X"). The reliability policy (an unreliable or unconfirmed value is never an error, it goes to review) stays in code.
5. **No applicant-entered values** for now (no declared 학번 or GPA/scale).

## Phases (after the merge; one at a time, each with all gates and the owner's OK)
- **Phase 0 (safety):** the server ignores any applicant-supplied check date (the checklist's check-date policy applies, default the submission date; a reviewer may override with a logged reason); remove applicant self-confirmation; remove the 2026-12-31 rule; minimal authentication on destructive and configuration endpoints; regression tests proving an applicant cannot reach 제출 가능 through the date or through confirmation; update the demo scenarios and the rehearsal.
- **Phase 1:** login and roles.
- **Phase 2:** versioned checklists and the editor.
- **Phase 3:** reviewer queue in the admin app, impact preview, audit log, rollback.
