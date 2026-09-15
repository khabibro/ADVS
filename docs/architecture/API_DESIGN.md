# API Design

All endpoints are under `/api/v1`; OpenAPI is available at `/docs`.

Groups:
- Health: `GET /health`
- Projects: `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`
- Checklists: `GET/POST /checklists`, `GET/PATCH /checklists/{id}`
- Documents: `POST /projects/{project_id}/documents`, `GET /projects/{project_id}/documents`, `GET/DELETE /documents/{document_id}`
- Processing: `POST /documents/{document_id}/process`, `GET /documents/{document_id}/processing-status`
- Verification: `POST /projects/{project_id}/verify`, `GET /projects/{project_id}/verification`, `GET /projects/{project_id}/verification-history`

Errors use machine-readable codes such as `INVALID_FILE_TYPE`, `FILE_TOO_LARGE`, `OCR_PROVIDER_ERROR`, and `RESOURCE_NOT_FOUND`.

