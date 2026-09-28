# Phase 8 baseline frontend audit

Date: 2026-09-28 (Asia/Seoul)

The audit was completed against the unchanged Phase 7 checkpoint (`6a73d37`) using the
Docker Compose application, the live browser UI, direct HTTP inspection, and container
logs. Test data was limited to local synthetic records and the read-only mentor PDFs.

| Page / flow | Action | Observed behavior | Expected behavior | Evidence / likely cause | Severity | Planned fix |
| --- | --- | --- | --- | --- | --- | --- |
| Application shell | Visit normal user routes | Navigation exposes checklist configuration and a placeholder verification-history page. | Task-oriented navigation for submissions and creating a new submission. | The root layout links directly to backend-oriented/unfinished routes. | Medium | Replace with a compact user-facing header and stable project navigation. |
| Project list | Load `/projects` | API failures are converted to an empty list, so an outage looks like “no projects”; the empty state is blank. | Distinguish loading, empty, and unavailable states with a recovery action. | `ProjectsListPage` catches every error and returns `[]`. | High | Add intentional error/empty states and retain structured API errors. |
| New project | Select a workflow | Requirements are visible, but the workflow is a plain select and required/optional importance is visually weak. | Explain each backend-provided workflow and clearly distinguish required from optional documents. | Single form layout with minimal hierarchy. | Medium | Add workflow cards, document requirement chips, validation, and pending feedback. |
| Project workspace | Open a populated project | Documents appear as a long undifferentiated list; required document status, verification, issues, and review are not combined into one workspace. | One page should answer what is missing, processing, ready, or awaiting review and provide the next action. | Page only fetches project and document summaries. | Critical | Build a query-backed project workspace with requirements, documents, verification, issues, and review queue. |
| Required documents | View a project | A processed file is treated as “confirmed” solely from detected type, and optional absence has no dedicated neutral state. | Present upload/processing/type state without inventing verification meaning; optional absence must not look erroneous. | Frontend derives a `completedDocumentTypes` set and labels matches `확인됨`. | High | Use explicit upload/processing wording and backend verification separately. |
| Upload selection | Open `/projects/{id}/upload` | Accepts PDF, PNG, JPG, and JPEG despite the PDF-first product flow; no selected size, maximum-size guidance, drag/drop, or field reset. | Reliable PDF selection with filename, size, validation, retry, and same-file reselection. | Minimal uncontrolled file input. | High | Create a reusable PDF upload component with client usability validation and input reset. |
| Upload mutation | Submit a file | Upload and OCR processing are one opaque action. The button is not disabled while running, so duplicate uploads are possible. | Upload success and processing success must be distinct; mutations must be guarded. | No pending state; sequential calls live inside one click handler. API logs show repeated uploads are accepted. | Critical | Separate visible stages, disable duplicate actions, and expose recovery paths. |
| Upload errors | Upload unsupported/corrupt content | Backend returns useful structured errors, but the UI discards them and always shows one generic sentence. | Show a natural Korean message for file type, size, corruption, connectivity, and processing failure. | `request()` throws `Error("API error <status>")` without parsing `detail`. | Critical | Add centralized `ApiError` parsing and Korean error normalization. |
| Uploaded filename | Upload a Korean-named mentor PDF | Upload succeeds, but the persisted filename becomes underscores (for example, Korean portions of a file name disappear). | Preserve a safe, recognizable display filename. | Backend `sanitize_filename()` permits only ASCII although storage uses a UUID key. | High | Preserve normalized Unicode display names while stripping path/control characters; add regression tests. |
| Processing | Complete upload | UI navigates only after synchronous processing returns and provides no separate processing, UNKNOWN, or failed recovery state. | Display uploaded, analyzing, completed, failed, and UNKNOWN states independently. | Upload page awaits `/process` before navigation; no status polling/retry UI. | High | Show real backend states and expose process/retry actions without fake progress. |
| Document detail | Inspect extraction | Canonical field names and enum-like values are shown directly; effective reviewed values and evidence sufficiency are absent. | Human-readable labels, effective value source, evidence context, and accessible status. | Detail page renders `field_name` and `normalized_value` directly. | High | Add centralized presentation mappings and effective-value display. |
| Verification | Use normal UI | No UI can run submission verification, set the evaluation date, view current/stale results, or act on issues. | Full verification and re-verification journey from the project page. | Phase 6/7 endpoints are not present in the frontend API client. | Critical | Integrate generated verification contracts and render authoritative backend results. |
| Human review | Use normal UI | Review queue and all four decisions are unavailable, forcing use of Swagger/API. | Review uncertain/missing fields, submit decisions, then visibly re-verify. | Phase 7 endpoints are unused by the frontend. | Critical | Build review queue/dialog interactions from backend review items. |
| Status/copy | Browse pages | Several backend values can fall through as raw enums; READY context is inconsistent. | Central Korean presentation mappings and a pre-check disclaimer. | `StatusBadge` falls back to the raw status string. | Medium | Centralize status/issue/field copy and never recalculate rule outcomes. |
| Page resilience | Trigger missing/unavailable data | There are no route loading/error/not-found boundaries; some requests silently degrade while others crash the page. | Intentional loading and recoverable error experiences. | Missing App Router boundary files and inconsistent catches. | High | Add shared loading/error/not-found components and query error states. |
| Frontend tests | Run `pnpm test` | The web test script only prints that no component tests exist. | Meaningful behavior tests for upload, verification, issues, review, and error normalization. | Placeholder package script and no test environment. | High | Add Vitest and React Testing Library with behavior-focused coverage. |

## Upload reproduction notes

- A real multipart request with field name `file` and a valid mentor PDF returned `201`.
- Processing the uploaded document separately returned `200` and `COMPLETED`, proving the
  upload contract and Phase 4 processing path work independently.
- An unsupported text upload returned `400 / INVALID_FILE_TYPE`.
- A deliberately corrupt PDF returned `400 / CORRUPT_DOCUMENT`.
- The unchanged UI cannot communicate these distinct results because it drops the
  structured error payload and combines upload with processing.
- The unchanged UI also allows repeat mutation clicks and does not reset the file input,
  making duplicate upload and same-file retry behavior unreliable.

No mentor PDF was modified, copied into the repository, or included in this artifact.
