import {
  apiJsonRequest,
  apiRequest,
  apiUploadRequest,
} from "@/lib/api-client";
import type {
  Document,
  DocumentDetail,
  FieldReview,
  FieldReviewCreate,
  Project,
  ProjectCreate,
  ReviewItem,
  Verification,
  Workflow,
} from "@/types/api";

/**
 * Typed endpoint map. Components call these functions and never build URLs.
 *
 * Mutation semantics that matter to the UI:
 * - `uploadDocument` stores a file only; it does not analyse anything.
 * - `processDocument` runs the full pipeline and resolves with the terminal
 *   document. The backend claims each document atomically, so a repeated call
 *   returns the in-flight document instead of running the pipeline twice.
 * - Any input mutation invalidates submission verification server-side.
 */
export const api = {
  workflows: () => apiRequest<Workflow[]>("/workflows"),

  projects: () => apiRequest<Project[]>("/projects"),
  project: (projectId: string) =>
    apiRequest<Project>(`/projects/${projectId}`),
  createProject: (body: ProjectCreate) =>
    apiJsonRequest<Project>("/projects", "POST", body),

  documents: (projectId: string) =>
    apiRequest<Document[]>(`/projects/${projectId}/documents`),
  document: (documentId: string) =>
    apiRequest<DocumentDetail>(`/documents/${documentId}`),
  uploadDocument: (projectId: string, file: File) =>
    apiUploadRequest<Document>(`/projects/${projectId}/documents`, file),
  processDocument: (documentId: string) =>
    apiJsonRequest<Document>(`/documents/${documentId}/process`, "POST"),

  verification: (projectId: string) =>
    apiRequest<Verification>(`/projects/${projectId}/verification`),
  verify: (projectId: string, evaluationDate: string) =>
    apiJsonRequest<Verification>(`/projects/${projectId}/verify`, "POST", {
      evaluation_date: evaluationDate,
    }),

  reviewItems: (projectId: string) =>
    apiRequest<ReviewItem[]>(`/projects/${projectId}/review-items`),
  reviews: (projectId: string, includeHistory = false) =>
    apiRequest<FieldReview[]>(
      `/projects/${projectId}/reviews?include_history=${includeHistory}`,
    ),
  submitReview: (
    projectId: string,
    documentId: string,
    fieldName: string,
    body: FieldReviewCreate,
  ) =>
    apiJsonRequest<FieldReview>(
      `/projects/${projectId}/documents/${documentId}/fields/${encodeURIComponent(fieldName)}/review`,
      "POST",
      body,
    ),
};
