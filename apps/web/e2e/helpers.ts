import { readFileSync } from "node:fs";
import path from "node:path";
import type { APIRequestContext } from "@playwright/test";

export const API = process.env.API_URL ?? "http://localhost:8000/api/v1";
const REPO = path.resolve(__dirname, "../../..");
const VARIANTS = path.join(REPO, "evaluation/datasets/synthetic/test_variants");
export const SUBMISSION_DATE = "2026-10-05";

type Code = "D1" | "D2" | "D3" | "D4" | "D5" | "D6" | "D7" | "D8";
const SCENARIOS: Record<Code, { set: string; version: "digital" | "scanned"; workflow: string }> = {
  D1: { set: "B01", version: "digital", workflow: "기업 제출서류 점검" },
  D2: { set: "B05", version: "digital", workflow: "기업 제출서류 점검" },
  D3: { set: "B03", version: "digital", workflow: "기업 제출서류 점검" },
  D4: { set: "B02", version: "digital", workflow: "기업 제출서류 점검" },
  D5: { set: "B11", version: "digital", workflow: "기업 제출서류 점검" },
  D6: { set: "B01", version: "scanned", workflow: "기업 제출서류 점검" },
  D7: { set: "S01", version: "digital", workflow: "학생 제출서류 점검" },
  D8: { set: "B08", version: "digital", workflow: "기업 제출서류 점검" },
};

export function scenarioFiles(code: Code): string[] {
  const { set, version } = SCENARIOS[code];
  const manifest = JSON.parse(readFileSync(path.join(VARIANTS, "manifest.json"), "utf8"));
  const entry = [...manifest.business_sets, ...manifest.student_sets].find((s: { set_id: string }) => s.set_id === set);
  return entry.files[version].map((rel: string) => path.join(VARIANTS, rel));
}

export function variantFile(rel: string): string {
  return path.join(VARIANTS, rel);
}

/** Creates a fresh submission for a demo scenario through the real API (the pre-loaded ones stay untouched). */
export async function createScenarioProject(
  request: APIRequestContext,
  code: Code,
  name: string,
  opts: { skipFirstFile?: boolean } = {},
): Promise<string> {
  const { workflow } = SCENARIOS[code];
  const workflows = await (await request.get(`${API}/workflows`)).json();
  const workflowId = workflows.find((w: { name: string }) => w.name === workflow).id;
  const project = await (await request.post(`${API}/projects`, { data: { name, workflow_id: workflowId } })).json();
  const files = scenarioFiles(code).slice(opts.skipFirstFile ? 1 : 0);
  for (const file of files) {
    const document = await (
      await request.post(`${API}/projects/${project.id}/documents`, {
        multipart: { file: { name: path.basename(file).normalize("NFC"), mimeType: "application/pdf", buffer: readFileSync(file) } },
      })
    ).json();
    await request.post(`${API}/documents/${document.id}/process`, { timeout: 300_000 });
  }
  await request.post(`${API}/projects/${project.id}/verify`, { data: { evaluation_date: SUBMISSION_DATE } });
  return project.id as string;
}

export async function deleteProject(request: APIRequestContext, id: string) {
  await request.delete(`${API}/projects/${id}`);
}

export async function demoProjects(request: APIRequestContext) {
  const projects: Array<{ id: string; name: string }> = await (await request.get(`${API}/projects`)).json();
  return projects.filter((p) => /^D\d /.test(p.name)).sort((a, b) => a.name.localeCompare(b.name));
}
