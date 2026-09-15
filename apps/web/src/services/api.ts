import type { Checklist, Document, DocumentDetail, Project, ProjectCreate, Workflow } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, cache: "no-store" });
  if (!response.ok) throw new Error(`API error ${response.status}`);
  return response.json() as Promise<T>;
}

export const api = {
  projects: () => request<Project[]>("/projects"),
  project: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (body: ProjectCreate) => request<Project>("/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  workflows: () => request<Workflow[]>("/workflows"),
  workflow: (id: string) => request<Workflow>(`/workflows/${id}`),
  checklists: () => request<Checklist[]>("/checklists"),
  checklist: (id: string) => request<Checklist>(`/checklists/${id}`),
  documents: (projectId: string) => request<Document[]>(`/projects/${projectId}/documents`),
  document: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  processDocument: (id: string) => request<Document>(`/documents/${id}/process`, { method: "POST" }),
  uploadDocument: async (projectId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Document>(`/projects/${projectId}/documents`, { method: "POST", body: form });
  },
};
