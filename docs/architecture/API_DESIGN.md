# API Design

All endpoints are under `/api/v1`; OpenAPI is available at `/docs`.

Groups:
- Health: `GET /health`
- Workflows: `GET /workflows`, `GET /workflows/{id}`. These are active `Checklist` records exposed in product language, including required/optional document requirements.
- Projects: `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`. Create/update requires `workflow_id`; reads include the selected workflow and expected documents.
- Checklists: `GET/POST /checklists`, `GET/PATCH /checklists/{id}`
- Admin (점검 기준 관리, used by the admin console; requires `X-ADVS-Admin-Token` when `ADMIN_API_TOKEN` is set):
  - `GET /admin/catalog`: document types and their fields, with Korean names and value kinds
  - `GET/POST /admin/workflows`, `GET/PATCH /admin/workflows/{id}`: list, create (optionally copying another workflow's criteria), rename, describe, activate/deactivate
  - `PUT /admin/workflows/{id}/criteria`: replace the criteria as a new version (required/optional documents, issue-date age, validity check, value conditions, comparisons between documents). Validated by the verification engine's own configuration check before anything is written (`422` with a `field` path); `expected_version` gives `409 VERSION_CONFLICT` if someone saved first. Saving invalidates stored results of projects that use the workflow.
  - `GET /admin/workflows/{id}/revisions`, `POST /admin/workflows/{id}/revisions/{version}/restore`: version history (editor, note, full criteria) and restore as a new version
- Workflow reads (`GET /workflows`, project overview) include `checks`: short Korean descriptions of each document's configured checks, shown to applicants before upload.
- Documents: `POST /projects/{project_id}/documents`, `GET /projects/{project_id}/documents`, `GET/DELETE /documents/{document_id}`
- Processing: `POST /documents/{document_id}/process`, `GET /documents/{document_id}/processing-status`
- Verification: `POST /projects/{project_id}/verify`, `GET /projects/{project_id}/verification`, `GET /projects/{project_id}/verification-history`

Errors use machine-readable codes such as `INVALID_FILE_TYPE`, `FILE_TOO_LARGE`, `OCR_PROVIDER_ERROR`, and `RESOURCE_NOT_FOUND`.

Canonical pre-check results are `READY`, `REVIEW_REQUIRED`, and `NEEDS_CORRECTION`. They are distinct from document processing states such as `PROCESSING`, `COMPLETED`, and `FAILED`. `READY` only means that the configured ADVS checks found no issue; it is not official approval.

Submission verification is explicit: `POST /projects/{project_id}/verify` requires an
`evaluation_date` and returns structured rule outcomes and issues. `GET
/projects/{project_id}/verification` reads the persisted latest result without rerunning OCR.
An input mutation invalidates that result, returning `is_current=false` until re-verification.
