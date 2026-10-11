// Capture screenshots of the demo screens with Playwright (Chromium).
//   node scripts/demo_screenshots.mjs <outDir> [width] [height]      pre-loaded demo screens
//   FLOW=1 node scripts/demo_screenshots.mjs <outDir> ...            + review flow, upload flow, errors
// Env: WEB_URL (default http://localhost:3000), API_URL (default http://localhost:8000/api/v1)
// FLOW creates temporary projects through the API and deletes them at the end.
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(root, "apps/web/package.json"));
const { chromium } = require("@playwright/test");

const web = process.env.WEB_URL ?? "http://localhost:3000";
const api = process.env.API_URL ?? "http://localhost:8000/api/v1";
const [out, width, height] = [process.argv[2] ?? "screenshots", Number(process.argv[3] ?? 1280), Number(process.argv[4] ?? 720)];
mkdirSync(out, { recursive: true });
const TV = path.join(root, "evaluation/datasets/synthetic/test_variants");
const j = async (url, init) => (await fetch(url, init)).json();

const projects = await j(`${api}/projects`);
const byCode = Object.fromEntries(projects.filter((p) => /^D\d /.test(p.name)).map((p) => [p.name.slice(0, 2), p]));

const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width, height } })).newPage();
const notes = [];
const shot = async (name, fullPage = true) => {
  await page.waitForTimeout(700);
  await page.addStyleTag({ content: "header{position:static !important}" });
  const wide = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (wide) notes.push(`HORIZONTAL OVERFLOW on ${name}`);
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage });
  console.log("saved", name);
};
const go = (u) => page.goto(`${web}${u}`, { waitUntil: "networkidle" });

await go("/projects");
await shot("00_projects_list");
for (const [code, project] of Object.entries(byCode).sort()) {
  await go(`/projects/${project.id}`);
  await shot(`${code}_workspace`);
}
// Evidence: a document with its page image and a highlighted field
const d6docs = byCode.D6 ? await j(`${api}/projects/${byCode.D6.id}/documents`) : [];
if (byCode.D6 && d6docs.length) {
  const tax = d6docs.find((d) => d.original_filename.includes("납세")) ?? d6docs[0];
  await go(`/projects/${byCode.D6.id}/documents/${tax.id}#field-valid_until`);
  await shot("D6_document_detail", false);
}
if (byCode.D2) {
  const docs = await j(`${api}/projects/${byCode.D2.id}/documents`);
  const tax = docs.find((d) => d.original_filename.includes("납세"));
  await go(`/projects/${byCode.D2.id}/documents/${tax.id}#field-valid_until`);
  await shot("D2_document_detail", false);
}

if (process.env.FLOW === "1") {
  const created = [];
  const workflow = (await j(`${api}/workflows`)).find((w) => w.name === "기업 제출서류 점검");
  const newProject = async (name) => {
    const p = await j(`${api}/projects`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name, workflow_id: workflow.id }) });
    created.push(p.id);
    return p;
  };

  // Review flow on a fresh copy of D9: confirm with the keyboard; the status updates by itself.
  const py = path.join(root, "apps/api/.venv312/bin/python");
  const d6 = execFileSync(py, ["-I", path.join(root, "scripts/demo_scenarios.py"), "run", "D9", "[캡처] D9 사람 확인"], { encoding: "utf8", env: { ...process.env, ADVS_API_URL: api } }).trim();
  created.push(d6);
  await go(`/projects/${d6}`);
  await shot("R1_review_needed");
  await page.getByRole("heading", { name: /^확인할 항목 \d+개$/ }).scrollIntoViewIfNeeded();
  await shot("R2_review_list", false);
  const confirm = page.getByRole("button", { name: /원본과 같음/ });
  await confirm.first().focus();
  // D9 leaves two dates for a person: confirm the first, look at the progress, confirm the last.
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { name: "확인할 항목 1개" }).waitFor();
  await shot("R3_review_progress", false);
  await page.keyboard.press("Enter");
  await page.locator('section[aria-labelledby="status-heading"]').getByRole("heading", { name: "제출 가능" }).waitFor({ timeout: 30000 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await shot("R4_ready_after_review");

  // Upload flow: empty submission, then a scanned PDF into its row
  const fresh = await newProject("[캡처] 라이브 업로드");
  await go(`/projects/${fresh.id}`);
  await shot("U0_empty_submission");
  const row = page.getByRole("heading", { name: "국세 납세증명서" }).locator("xpath=ancestor::li[1]");
  await row.locator('input[type="file"]').setInputFiles(path.join(TV, "business/B01_all_valid/scanned/B01-3_납세증명서_스캔.pdf"));
  await page.waitForTimeout(3500);
  await shot("U1_processing", false);
  await page.getByText(/1개 서류의 분석이 끝났습니다/).waitFor({ timeout: 120000 });
  await shot("U2_after_upload");

  // Errors
  const bad = await newProject("[캡처] 업로드 오류");
  await go(`/projects/${bad.id}`);
  await page.getByTestId("upload-input").setInputFiles(path.join(TV, "formats/F16_corrupt_files/F16a_사업자등록증_손상.pdf"));
  await page.getByRole("alert").first().waitFor();
  await shot("E1_corrupt_file", false);
  writeFileSync(path.join(out, "_memo.txt"), "hello");
  await page.getByTestId("upload-input").setInputFiles(path.join(out, "_memo.txt"));
  await page.getByText(/지원하지 않는 파일 형식/).first().waitFor();
  await shot("E2_unsupported_type", false);
  for (const id of created) await fetch(`${api}/projects/${id}`, { method: "DELETE" });
}
console.log(notes.length ? notes.join("\n") : `no horizontal overflow at ${width}x${height}`);
await browser.close();
