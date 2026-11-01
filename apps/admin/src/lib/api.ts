import type { components } from "@advs/contracts/openapi";
import type { Catalog, RuleDocument } from "./document";

type Schemas = components["schemas"];
export type WorkflowSummary = Schemas["AdminWorkflowSummary"];
export type WorkflowRead = Schemas["AdminWorkflowRead"];
export type VersionRead = Schemas["VersionRead"];
export type VersionSummary = Schemas["VersionSummary"];
export type Problem = Schemas["ProblemRead"];
export type Warning = Schemas["WarningRead"];
export type PreviewRead = Schemas["PreviewRead"];
export type PreviewSource = Schemas["PreviewSourceRead"];
export type DiffRead = Schemas["DiffRead"];
export type AuditRead = Schemas["AuditRead"];
export type QueueRead = Schemas["QueueRead"];
export type QueueItem = Schemas["QueueItemRead"];
export type ReviewDetail = Schemas["ReviewDetailRead"];
export type ReviewLog = Schemas["ReviewLogRead"];
export type ReviewDecision = "CONFIRMED" | "CORRECTED" | "REJECTED" | "CANNOT_DETERMINE";
export type ValidationRead = Schemas["ChecklistCheckRead"];

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class AdminApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly problems: Problem[] = [],
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}/admin${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new AdminApiError(
      0,
      "NETWORK",
      "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
    );
  }
  if (response.status === 204) return undefined as T;
  const body = (await response.json().catch(() => null)) as {
    detail?: { code?: string; message?: string; problems?: Problem[] };
  } | null;
  if (!response.ok) {
    const detail = body?.detail;
    throw new AdminApiError(
      response.status,
      detail?.code ?? "ERROR",
      detail?.message ?? "요청을 처리하지 못했습니다.",
      detail?.problems ?? [],
    );
  }
  return body as T;
}

const json = (value: unknown) => JSON.stringify(value);

export const adminApi = {
  catalog: () => request<Catalog>("/catalog"),
  workflows: () => request<WorkflowSummary[]>("/workflows"),
  workflow: (id: string) => request<WorkflowRead>(`/workflows/${id}`),
  versions: (id: string) =>
    request<VersionSummary[]>(`/workflows/${id}/versions`),
  version: (id: string, n: number) =>
    request<VersionRead>(`/workflows/${id}/versions/${n}`),
  validate: (id: string, document: RuleDocument) =>
    request<ValidationRead>(`/workflows/${id}/validate`, {
      method: "POST",
      body: json({ document }),
    }),
  saveDraft: (
    id: string,
    document: RuleDocument,
    expectedRevision: number | null,
  ) =>
    request<Schemas["DraftSaved"]>(`/workflows/${id}/draft`, {
      method: "PUT",
      body: json({ document, expected_revision: expectedRevision }),
    }),
  discardDraft: (id: string) =>
    request<void>(`/workflows/${id}/draft`, { method: "DELETE" }),
  preview: (id: string) =>
    request<PreviewRead>(`/workflows/${id}/draft/preview`, { method: "POST" }),
  diff: (id: string, from?: number, to?: number) => {
    const query = new URLSearchParams();
    if (from !== undefined) query.set("from", String(from));
    if (to !== undefined) query.set("to", String(to));
    return request<DiffRead>(`/workflows/${id}/diff?${query}`);
  },
  publish: (
    id: string,
    changeNote: string,
    acknowledged: string[],
    expectedRevision: number,
  ) =>
    request<VersionRead>(`/workflows/${id}/publish`, {
      method: "POST",
      body: json({
        change_note: changeNote,
        acknowledged_warnings: acknowledged,
        expected_revision: expectedRevision,
      }),
    }),
  rollback: (id: string, toVersion: number, changeNote: string) =>
    request<VersionRead>(`/workflows/${id}/rollback`, {
      method: "POST",
      body: json({ to_version: toVersion, change_note: changeNote }),
    }),
  audit: (checklistId?: string) =>
    request<AuditRead[]>(
      `/audit${checklistId ? `?checklist_id=${checklistId}` : ""}`,
    ),
};

export interface QueueQuery {
  status: string;
  workflow: string;
  document: string;
  field: string;
  q: string;
  oneClick: boolean;
  sort: string;
}

export const pageImageUrl = (documentId: string, page: number) =>
  `${BASE}/documents/${documentId}/pages/${page}/image`;

export const reviewApi = {
  queue: (query: QueueQuery) => {
    const params = new URLSearchParams({ status: query.status, sort: query.sort });
    if (query.workflow) params.set("workflow", query.workflow);
    if (query.document) params.set("document_type", query.document);
    if (query.field) params.set("field_name", query.field);
    if (query.q.trim()) params.set("q", query.q.trim());
    if (query.oneClick) params.set("one_click", "true");
    return request<QueueRead>(`/review-queue?${params}`);
  },
  detail: (projectId: string, documentId: string, field: string) =>
    request<ReviewDetail>(`/review-queue/${projectId}/${documentId}/${field}`),
  log: (decision: string, offset: number) => {
    const params = new URLSearchParams({ limit: "50", offset: String(offset) });
    if (decision) params.set("decision", decision);
    return request<ReviewLog>(`/review-log?${params}`);
  },
  /** The existing review endpoint; the server stays the only judge of what a decision does. */
  decide: async (
    projectId: string,
    documentId: string,
    field: string,
    body: {
      decision: ReviewDecision;
      expected_processing_version: number;
      corrected_value?: string;
      note?: string;
    },
  ) => {
    let response: Response;
    try {
      response = await fetch(
        `${BASE}/projects/${projectId}/documents/${documentId}/fields/${field}/review`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ ...body, reviewer_label: "관리자" }),
        },
      );
    } catch {
      throw new AdminApiError(0, "NETWORK", "서버에 연결할 수 없습니다.");
    }
    if (response.ok) return;
    const payload = (await response.json().catch(() => null)) as {
      detail?: { code?: string; message?: string };
    } | null;
    throw new AdminApiError(
      response.status,
      payload?.detail?.code ?? "ERROR",
      payload?.detail?.message ?? "요청을 처리하지 못했습니다.",
    );
  },
};
