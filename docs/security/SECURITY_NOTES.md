# Security notes — no login yet

ADVS has no accounts. These notes say what is protected today, what is not, and what login must
add before any real deployment. They describe the code on `feature/admin-checklists`.

## What is protected

| Protection | How | Where |
|---|---|---|
| Applicant cannot choose the check date | The server decides it (`CHECK_DATE_MODE`: the submission date, stored once at the first check, or a fixed admin date). A client-sent `evaluation_date` is ignored unless `ALLOW_CLIENT_EVALUATION_DATE=true`, which is for test harnesses only (startup warning; each stored check records `client_supplied_test_mode`). | `app/core/access.py` |
| Applicant cannot confirm or correct values | The review endpoint answers 404 unless `ADMIN_ENABLED=true`. An applicant sees "담당자 확인 중" only. | `routes.py` |
| Applicant cannot edit checklists or delete a submission | Same switch: `POST/PATCH /checklists`, `DELETE /projects/{id}` and the explicit re-check `POST /projects/{id}/recheck` answer 404 unless `ADMIN_ENABLED=true`. The re-check needs a reason and writes an audit log row. | `routes.py` |
| A submission is reachable only with its link | Every route that names a project, or a document of one, needs that submission's random token (`X-Submission-Token` header, or `?token=` for image URLs). Wrong, missing or unknown gives 404 (existence is not revealed). The token is returned once, when the submission is created. | `access.py`, `projects.access_token` |
| No public list of submissions | `GET /projects` and `GET /project-summaries` answer 404 unless `ADMIN_ENABLED=true`. | `routes.py` |
| Uploads are cleaned | Size limits, MPO/GPS/metadata stripping, page and pixel limits (unchanged). | `services/storage/sanitize.py` |

Regression tests: `tests/test_phase0_access.py`, run with both switches off (the applicant
deployment) as well as with the test-mode conftest.

## What is NOT protected

- **No identity.** Anyone with a submission link is that applicant; anyone who can reach an
  `ADMIN_ENABLED=true` server is an admin and reviewer. Audit rows say "admin (no login yet)".
- **`ADMIN_ENABLED` is a per-process switch, not a separate port.** The applicant app and the
  admin tools share one API process in this build. The admin screens are meant to be served on an
  internal host or port; that split (and binding to localhost) arrives with the admin app.
- **Demo exposure (until review moves to the admin app, Phase 3).** `scripts/demo` runs with
  `ADMIN_ENABLED=true` because the current applicant web still contains the review screen. In the
  demo, therefore: submission tokens are not enforced, `GET /projects` works, and anyone reaching
  the demo API can confirm values, edit checklists and delete submissions. Do not expose the demo
  API to a network you do not control. The demo never enables `ALLOW_CLIENT_EVALUATION_DATE`; it
  uses `CHECK_DATE_MODE=fixed` (`2026-10-05`).
- Links are bearer secrets: anyone holding one can use it. They are not rotated, expired or
  revoked, and travel in URLs (`?token=` for images) that browsers and proxies may log.
- No rate limiting, no CSRF protection (there are no sessions), CORS is a fixed allow-list.
- Stored uploads are not encrypted at rest; SQLite is a single local file.

## What login must add before any real deployment

1. Accounts for applicants, reviewers and admins; roles enforced on the server for every admin
   route, replacing the `ADMIN_ENABLED` switch.
2. The admin API on a separate listener (internal network or VPN), not the applicant's.
3. Real actor names in the audit log; links tied to the applicant account, with expiry and
   revocation; tokens out of URLs.
4. Rate limiting and abuse limits on uploads and token guessing; HTTPS only.
5. Storage encryption, retention and deletion rules for uploaded documents (see
   `document-privacy.md`).
