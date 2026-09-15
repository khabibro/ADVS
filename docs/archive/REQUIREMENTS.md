# Requirements

## Functional
- FR-001 Users can create and list verification projects.
- FR-002 Users can upload PDF, PNG, JPG, and JPEG documents.
- FR-003 Backend stores files without exposing filesystem paths.
- FR-004 Backend chooses direct PDF text or OCR path.
- FR-005 System classifies four supported documents or UNKNOWN.
- FR-006 System extracts structured fields without hallucination.
- FR-007 System validates required documents, fields, dates, identity/company matching, duplicate files, and expected type.
- FR-008 Frontend displays projects, documents, extracted fields, statuses, and issues.

## Non-Functional
- NFR-001 Secrets must come from environment variables.
- NFR-002 Full OCR text and secrets must not be logged by default.
- NFR-003 Processing services must be replaceable for later queues and providers.
- NFR-004 PostgreSQL is the intended database.

## MVP
- MVP-001 Support exactly 졸업증명서, 경력증명서, 사업자등록증, 중소기업확인서.
- MVP-002 Use PaddleOCR abstraction and mock mode.
- MVP-003 Provide tests, Docker, migrations, seed data, and docs.

## Later Stage
- LS-001 Authentication and RBAC.
- LS-002 Manual review/edit workflow.
- LS-003 Accuracy benchmarking dataset.
- LS-004 Object storage, encryption, retention, observability, CI/CD.
