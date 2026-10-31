# Security notes — no login yet

ADVS has no accounts. These notes say what is protected today, what is not, and what login must
add before any real deployment. They describe the code on `feature/admin-checklists`.

## What is protected

| Protection | How | Where |
|---|---|---|
| Applicant cannot choose the check date | The server decides it (`CHECK_DATE_MODE`: today's date, or a fixed admin date). Draft checks use that date as a preview and store nothing; the applicant's explicit `POST /projects/{id}/finalise` ("제출하기") freezes it, every later check reuses it, and only the admin re-check changes it. A client-sent `evaluation_date` is ignored unless `ALLOW_CLIENT_EVALUATION_DATE=true`, which is for test harnesses only (startup warning; each stored check records `client_supplied_test_mode`). | `app/core/access.py` |
| Applicant cannot confirm or correct values | The review endpoint answers 404 unless `ADMIN_ENABLED=true`. An applicant sees "담당자 확인 중" only. | `routes.py` |
| Applicant cannot edit checklists or delete a submission | Same switch: `POST/PATCH /checklists`, `DELETE /projects/{id}` and the explicit re-check `POST /projects/{id}/recheck` answer 404 unless `ADMIN_ENABLED=true`. The re-check needs a reason and writes an audit log row. | `routes.py` |
| A submission is reachable only with its link | Every route that names a project, or a document of one, needs that submission's random token (`X-Submission-Token` header, or `?token=` for image URLs). Wrong, missing or unknown gives 404 (existence is not revealed). The token is returned once, when the submission is created. | `access.py`, `projects.access_token` |
| No public list of submissions | `GET /projects` and `GET /project-summaries` answer 404 unless `ADMIN_ENABLED=true`. | `routes.py` |
| A finalised submission cannot be changed | After "제출하기", uploads, edits and re-processing of a document answer 409 (`SUBMISSION_FINALISED`, "제출이 완료되었습니다. 수정하려면 제출을 취소하세요."). The applicant can reopen (`POST /projects/{id}/reopen`) only while no reviewer decision exists; afterwards only `POST /projects/{id}/admin-reopen` (admin, reason required). Both clear the frozen date and write an audit row. | `routes.py` |
| Link token stays out of Referers and logs | Every response carries `Referrer-Policy: no-referrer`. A log filter replaces any `?token=` value with `[redacted]` in the access and HTTP-client log lines. | `app/main.py`, `app/core/logging.py` |
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
- **Admin path = same process.** Re-processing a finalised document is allowed when `ADMIN_ENABLED=true` (and logged as "admin (no login yet)"). While admin and applicant share one process, as in the demo, an applicant can take that path too.
- Links are bearer secrets: anyone holding one can use it. They are not rotated, expired or
  revoked. Image requests carry the token in the URL (`?token=`, because `<img>` cannot send a
  header). The API sends `Referrer-Policy: no-referrer` and redacts the value in its own logs, but
  a reverse proxy, CDN or browser history in front of it can still record the URL: configure any
  proxy to drop query strings from access logs, and prefer a short-lived image URL once login exists.
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
