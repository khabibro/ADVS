// UX audit capture: every applicant/reviewer screen and edge state, at one viewport size.
//   node scripts/ux_audit.mjs <outDir> <width> <height>
// Env: WEB_URL (default http://localhost:3000), API_URL (default http://localhost:8000/api/v1)
// Creates temporary "[감사]" projects and deletes them at the end.
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(root, "apps/web/package.json"));
const { chromium } = require("@playwright/test");
const web = process.env.WEB_URL ?? "http://localhost:3000";
const api = process.env.API_URL ?? "http://localhost:8000/api/v1";
const [out, width, height] = [process.argv[2] ?? "audit", Number(process.argv[3] ?? 1440), Number(process.argv[4] ?? 900)];
mkdirSync(out, { recursive: true });
const TV = path.join(root, "evaluation/datasets/synthetic/test_variants");
const created = [];

const j = async (url, init) => (await fetch(url, init)).json();
const workflows = await j(`${api}/workflows`);
const wf = (n) => workflows.find((w) => w.name === n).id;
async function newProject(name, workflow = "기업 제출서류 점검") {
  const p = await j(`${api}/projects`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name, workflow_id: wf(workflow) }) });
  created.push(p.id);
  return p;
}
const demo = Object.fromEntries((await j(`${api}/projects`)).filter((p) => /^D\d /.test(p.name)).map((p) => [p.name.slice(0, 2), p]));

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width, height } });
const page = await ctx.newPage();
const notes = [];
page.on("pageerror", (e) => notes.push(`pageerror: ${e.message}`));
page.on("console", (m) => { if (m.type() === "error") notes.push(`console: ${m.text()}`); });
const shot = async (name, full = true) => {
  await page.waitForTimeout(700);
  await page.addStyleTag({ content: "header{position:static !important}" });
  const wide = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (wide) notes.push(`HORIZONTAL OVERFLOW on ${name}`);
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: full });
  console.log("saved", name);
};
const go = (u) => page.goto(`${web}${u}`, { waitUntil: "networkidle" });

// --- applicant: choose workflow, create
await go("/projects");
await shot("01_list");
await go("/projects/new");
await shot("02_new_project");
// --- demo results
for (const c of ["D1", "D2", "D3", "D5", "D6", "D8"]) {
  await go(`/projects/${demo[c].id}`);
  await shot(`03_${c}_workspace`);
}
// document detail (digital + scanned)
const docs = await j(`${api}/projects/${demo.D2.id}/documents`);
await go(`/projects/${demo.D2.id}/documents/${docs.find((d) => d.original_filename.includes("납세")).id}`);
await shot("04_document_detail_digital");
const d6docs = await j(`${api}/projects/${demo.D6.id}/documents`);
await go(`/projects/${demo.D6.id}/documents/${d6docs.find((d) => d.original_filename.includes("납세")).id}`);
await shot("05_document_detail_scanned");
// review editor
await go(`/projects/${demo.D6.id}`);
await page.getByRole("button", { name: /확인하기/ }).first().click();
await shot("06_review_editor", false);

// --- edge states: empty project and uploads through the UI
const empty = await newProject("[감사] 빈 제출 건");
await go(`/projects/${empty.id}`);
await shot("10_empty_project");
const input = () => page.locator('input[type="file"]');
const attempt = async (name, files, submit = true, wait = 4000) => {
  await go(`/projects/${empty.id}`);
  await input().setInputFiles(files);
  await page.waitForTimeout(400);
  await shot(`11_${name}_selected`, false);
  if (submit) {
    const btn = page.getByTestId("upload-submit");
    if (await btn.count()) {
      await btn.click();
      await page.waitForTimeout(wait);
      await shot(`12_${name}_result`);
    }
  }
};
const fs = await import("node:fs");
const tmp = path.join(out, "_tmp"); mkdirSync(tmp, { recursive: true });
writeFileSync(path.join(tmp, "메모.txt"), "hello");
writeFileSync(path.join(tmp, "빈파일.pdf"), "");
await attempt("unsupported_txt", path.join(tmp, "메모.txt"), false);
await attempt("empty_pdf", path.join(tmp, "빈파일.pdf"), false);
await attempt("docx", path.join(TV, "formats/F15_other_formats/F15_사업자등록증.docx"), false);
await attempt("jpg_image", path.join(TV, "business/B01_all_valid/images/B01-1_사업자등록증_사진.jpg"), false);
await attempt("corrupt_pdf", path.join(TV, "formats/F16_corrupt_files/F16a_사업자등록증_손상.pdf"));
await attempt("fake_extension", path.join(TV, "formats/F16_corrupt_files/F16c_사업자등록증_확장자위장.pdf"));
await attempt("multi_two_certs", path.join(TV, "formats/F13_multipage_two_certs/F13_사업자등록증.pdf"));
await attempt("unknown_local_tax", path.join(TV, "business/B11_local_tax_lookalike/digital/B11-3_지방세납세증명서.pdf").replace("B11_local_tax_lookalike", fs.readdirSync(path.join(TV, "business")).find((d) => d.startsWith("B11"))));
// same file twice (duplicate in the queue) then upload of a duplicate document
const b1 = path.join(TV, "business/B01_all_valid/digital/B01-1_사업자등록증.pdf");
await go(`/projects/${empty.id}`);
await input().setInputFiles([b1]);
await input().setInputFiles([b1]);
await shot("11_duplicate_in_queue", false);
// processing state: a scanned certificate, screenshot mid-analysis
const proj2 = await newProject("[감사] 스캔 업로드");
await go(`/projects/${proj2.id}`);
await input().setInputFiles(path.join(TV, "business/B01_all_valid/scanned/B01-3_납세증명서_스캔.pdf"));
await page.getByTestId("upload-submit").click();
await page.waitForTimeout(2500);
await shot("13_processing_scanned", false);
await page.getByText("분석 완료").first().waitFor({ timeout: 120000 });
await shot("14_scanned_done");
// duplicate document uploaded again (same bytes)
await input().setInputFiles(path.join(TV, "business/B01_all_valid/digital/B01-3_납세증명서.pdf"));
await page.getByTestId("upload-submit").click();
await page.waitForTimeout(3000);
await input().setInputFiles(path.join(TV, "business/B01_all_valid/digital/B01-3_납세증명서.pdf"));
await page.getByTestId("upload-submit").click();
await page.waitForTimeout(3000);
await shot("15_same_document_twice");

// --- API / network error
await page.route("**/api/v1/projects", (r) => r.abort());
await go("/projects").catch(() => {});
await shot("20_network_error_list", false);
await page.unroute("**/api/v1/projects");
await page.route("**/api/v1/projects/*/documents", (r) => (r.request().method() === "POST" ? r.abort() : r.continue()));
await go(`/projects/${empty.id}`);
await input().setInputFiles(b1);
await page.getByTestId("upload-submit").click();
await page.waitForTimeout(1500);
await shot("21_network_error_upload", false);
await page.unroute("**/api/v1/projects/*/documents");
await go("/projects/00000000-0000-0000-0000-000000000000");
await shot("22_not_found", false);

for (const id of created) await fetch(`${api}/projects/${id}`, { method: "DELETE" });
writeFileSync(path.join(out, "_notes.txt"), notes.join("\n"));
console.log(notes.length ? notes.join("\n") : "no console errors or overflow");
await browser.close();
