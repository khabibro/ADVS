# API Design

All endpoints are under `/api/v1`; OpenAPI is available at `/docs`.

Groups:
- Health: `GET /health`
- Workflows: `GET /workflows`, `GET /workflows/{id}`. These are active `Checklist` records exposed in product language, including required/optional document requirements.
- Projects: `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`. Create/update requires `workflow_id`; reads include the selected workflow and expected documents.
- Checklists: `GET/POST /checklists`, `GET/PATCH /checklists/{id}`
- Documents: `POST /projects/{project_id}/documents`, `GET /projects/{project_id}/documents`, `GET/DELETE /documents/{document_id}`
- Processing: `POST /documents/{document_id}/process`, `GET /documents/{document_id}/processing-status`
- Verification: `POST /projects/{project_id}/verify`, `GET /projects/{project_id}/verification`, `GET /projects/{project_id}/verification-history`

Errors use machine-readable codes such as `INVALID_FILE_TYPE`, `FILE_TOO_LARGE`, `OCR_PROVIDER_ERROR`, and `RESOURCE_NOT_FOUND`.

Canonical pre-check results are `READY`, `REVIEW_REQUIRED`, and `NEEDS_CORRECTION`. They are distinct from document processing states such as `PROCESSING`, `COMPLETED`, and `FAILED`. `READY` only means that the configured ADVS checks found no issue; it is not official approval.

Submission verification is explicit: `POST /projects/{project_id}/verify` requires an
`evaluation_date` and returns structured rule outcomes and issues. `GET
/projects/{project_id}/verification` reads the persisted latest result without rerunning OCR.
An input mutation invalidates that result, returning `is_current=false` until re-verification.
