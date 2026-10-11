// Captures the v4 deck screenshots from the running demo (fictional TEST SAMPLE documents only).
//   node docs/midterm/v4/capture_screenshots.mjs <outDir>      (needs: scripts/demo start; Playwright from apps/web)
// 1920x1080, deviceScaleFactor 2 (3840x2160 PNG). Writes <outDir>/<name>.png and meta.json (element boxes in CSS px,
// used by the deck builder to place callouts). Temporary projects are deleted at the end.
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const require = createRequire(path.join(root, "apps/web/package.json"));
const { chromium } = require("@playwright/test");
const web = process.env.WEB_URL ?? "http://localhost:3000";
const admin = process.env.ADMIN_URL ?? "http://localhost:3002";
const api = process.env.API_URL ?? "http://localhost:8000/api/v1";
const out = process.argv[2] ?? "screenshots";
mkdirSync(out, { recursive: true });
const TV = path.join(root, "evaluation/datasets/synthetic/test_variants");
const j = async (url, init) => (await fetch(url, init)).json();
const created = [];
const meta = {};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
const go = (u, base = web) => page.goto(`${base}${u}`, { waitUntil: "networkidle" });
const box = async (loc) => { try { return await loc.first().boundingBox({ timeout: 3000 }); } catch { return null; } };
const shot = async (name, boxes = {}) => {
  await page.waitForTimeout(600);
  await page.addStyleTag({ content: "header{position:static !important}" });
  const b = {};
  for (const [k, loc] of Object.entries(boxes)) b[k] = await box(loc);
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: false });
  meta[name] = { viewport: [1920, 1080], boxes: b };
  console.log("saved", name);
};
const projects = await j(`${api}/projects`);
const byCode = Object.fromEntries(projects.filter((p) => /^D\d /.test(p.name)).map((p) => [p.name.slice(0, 2), p]));
const banner = () => page.locator('section[aria-labelledby="status-heading"]');
const workflows = await j(`${api}/workflows`);
const newProject = async (name, wf = "기업 제출서류 점검") => {
  const p = await j(`${api}/projects`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name, workflow_id: workflows.find((w) => w.name === wf).id }) });
  created.push(p.id);
  return p;
};
const upload = async (projectId, files) => {
  for (const f of files) {
    const buf = readFileSync(f);
    const fd = new FormData();
    fd.append("file", new Blob([buf], { type: "application/pdf" }), path.basename(f).normalize("NFC"));
    const d = await (await fetch(`${api}/projects/${projectId}/documents`, { method: "POST", body: fd })).json();
    await fetch(`${api}/documents/${d.id}/process`, { method: "POST" });
  }
  await fetch(`${api}/projects/${projectId}/verify`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ evaluation_date: "2026-10-05" }) });
};

// S1 submission screen with two of four documents added through the real uploader
const s1 = await newProject("기업 제출 (신규)");
// two documents added (same API path as the demo scenarios, so the check date is the demo's 2026-10-05)
await upload(s1.id, [
  path.join(TV, "business/B01_all_valid/digital/B01-1_사업자등록증.pdf"),
  path.join(TV, "business/B01_all_valid/digital/B01-2_중소기업확인서.pdf"),
]);
await go(`/projects/${s1.id}`);
await shot("S1_upload", { banner: banner(), rows: page.getByRole("heading", { name: "제출 서류" }).locator("xpath=following::ul[1]"), dropzone: page.getByRole("heading", { name: "서류 추가" }).locator("xpath=ancestor::section[1]") });

// S2 D1 happy path
await go(`/projects/${byCode.D1.id}`);
await shot("S2_ready", { banner: banner(), rows: page.getByRole("heading", { name: "제출 서류" }).locator("xpath=following::ul[1]") });

// S3 evidence of one field (valid_until of the tax certificate in D1)
const d1docs = await j(`${api}/projects/${byCode.D1.id}/documents`);
const tax = d1docs.find((d) => d.original_filename.includes("납세"));
await go(`/projects/${byCode.D1.id}/documents/${tax.id}#field-valid_until`);
await page.evaluate(() => document.getElementById("field-valid_until")?.scrollIntoView({ block: "center" }));
await shot("S3_evidence", { viewer: page.getByTestId("page-viewer"), field: page.locator("#field-valid_until") });

// S4 D2 expired
await go(`/projects/${byCode.D2.id}`);
await shot("S4_expired", { banner: banner(), issue: page.getByText(/유효기간 종료일/).first() });

// S5 D3 name mismatch (company names differ) and D8 missing document
await go(`/projects/${byCode.D3.id}`);
await shot("S5_mismatch", { banner: banner(), issue: page.getByText(/≠|일치하지/).first() });
await go(`/projects/${byCode.D8.id}`);
await shot("S5b_missing", { banner: banner(), missing: page.getByText("미제출").first() });

// S6 D5 look-alike
await go(`/projects/${byCode.D5.id}`);
await shot("S6_lookalike", { banner: banner(), files: page.getByText(/지원하지 않는 서류|확인이 필요한 파일/).first() });

// S7 D9 review screen (the pre-loaded D9 stays untouched; a fresh copy is used for the flow)
const d9 = execFileSync(path.join(root, "apps/api/.venv312/bin/python"), ["-I", path.join(root, "scripts/demo_scenarios.py"), "run", "D9", "D9 스캔본 제출 (학생)"], { encoding: "utf8", env: { ...process.env, ADVS_API_URL: api } }).trim();
created.push(d9);
await go(`/projects/${d9}`);
await page.evaluate(() => { const h = [...document.querySelectorAll("h2")].find((e) => /^확인할 항목 \d+개$/.test(e.textContent.trim())); window.scrollTo(0, h.getBoundingClientRect().top + window.scrollY - 70); });
await shot("S7_review", { card: page.getByTestId("review-card"), crop: page.getByTestId("evidence-crop"), confirm: page.getByRole("button", { name: /원본과 같음/ }) });

// S8 after the review: automatic re-check
const confirm = page.getByRole("button", { name: /원본과 같음/ });
await confirm.first().focus();
await page.keyboard.press("Enter");
await page.getByRole("heading", { name: "확인할 항목 1개" }).waitFor();
await page.keyboard.press("Enter");
await banner().getByRole("heading", { name: "제출 가능" }).waitFor({ timeout: 30000 });
await page.evaluate(() => window.scrollTo(0, 0));
await shot("S8_after_review", { banner: banner(), changed: page.getByText(/방금 확인 필요/).first() });

// S9 a PDF with hidden text: the page shows one date, the text layer says another
mkdirSync(path.join(os.tmpdir(), "v4tamper"), { recursive: true });
const tamperedPath = path.join(os.tmpdir(), "v4tamper", "B01-3_납세증명서.pdf");
const tampered = execFileSync(path.join(root, "apps/api/.venv312/bin/python"), ["-I", path.join(root, "docs/midterm/v4/make_tampered_pdf.py"), TV, tamperedPath], { encoding: "utf8" }).trim();
const s9 = await newProject("위·변조 PDF 시험");
await upload(s9.id, [
  path.join(TV, "business/B01_all_valid/digital/B01-1_사업자등록증.pdf"),
  path.join(TV, "business/B01_all_valid/digital/B01-2_중소기업확인서.pdf"),
  tamperedPath,
  path.join(TV, "business/B01_all_valid/digital/B01-4_4대사회보험료완납증명서.pdf"),
]);
await go(`/projects/${s9.id}`);
await shot("S9_tampered", { banner: banner(), issue: page.getByText(/숨은 글자/).first() });

// S10 admin
await go("/", admin);
await shot("S10_admin", {});
for (const id of created) await fetch(`${api}/projects/${id}`, { method: "DELETE" });
writeFileSync(path.join(out, "meta.json"), JSON.stringify(meta, null, 1));
await browser.close();
console.log("done");
