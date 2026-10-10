// Capture screenshots of the demo screens with Playwright (Chromium).
//   node scripts/demo_screenshots.mjs <outDir> [width] [height]
// Env: WEB_URL (default http://localhost:3000), API_URL (default http://localhost:8000/api/v1)
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(root, "apps/web/package.json"));
const { chromium } = require("@playwright/test");

const web = process.env.WEB_URL ?? "http://localhost:3000";
const api = process.env.API_URL ?? "http://localhost:8000/api/v1";
const out = process.argv[2] ?? "screenshots";
const width = Number(process.argv[3] ?? 1280);
const height = Number(process.argv[4] ?? 720);
mkdirSync(out, { recursive: true });

const projects = await (await fetch(`${api}/projects`)).json();
const byCode = Object.fromEntries(
  projects.filter((p) => /^D\d /.test(p.name)).map((p) => [p.name.slice(0, 2), p]),
);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height } });
const overflow = [];
const shot = async (name, fullPage = true) => {
  await page.waitForTimeout(800);
  await page.addStyleTag({ content: "header{position:static !important}" });
  const wide = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (wide) overflow.push(name);
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage });
  console.log("saved", name);
};

await page.goto(`${web}/projects`, { waitUntil: "networkidle" });
await shot("00_projects_list");
for (const [code, project] of Object.entries(byCode)) {
  await page.goto(`${web}/projects/${project.id}`, { waitUntil: "networkidle" });
  await shot(`${code}_workspace`);
}
const admin = process.env.ADMIN_URL ?? "http://localhost:3002";
for (const [name, route] of [["A1_admin_dashboard", "/"], ["A2_admin_projects", "/projects"]]) {
  await page.goto(`${admin}${route}`, { waitUntil: "networkidle" });
  await shot(name);
}
await page.goto(`${web}/projects`, { waitUntil: "networkidle" });

if (process.env.FLOW === "1") {
  // Review round trip on a fresh copy of D6 (the pre-loaded demo projects stay untouched).
  const py = path.join(root, "apps/api/.venv312/bin/python");
  const id = execFileSync(py, ["-I", path.join(root, "scripts/demo_scenarios.py"), "run", "D6", "[캡처] D6 사람 확인"], { encoding: "utf8" }).trim();
  await page.goto(`${web}/projects/${id}`, { waitUntil: "networkidle" });
  await shot("R1_review_needed");
  await page.getByRole("button", { name: /확인하기/ }).first().click();
  await shot("R2_review_editor", false);
  await page.getByRole("button", { name: "닫기" }).first().click();
  for (let i = 0; i < 4; i++) {
    await page.getByRole("button", { name: /확인하기/ }).first().click();
    await page.getByRole("button", { name: "검토 저장" }).first().click();
    await page.getByText("검토 저장").first().waitFor({ state: "detached", timeout: 15000 });
    await page.waitForTimeout(500);
  }
  await shot("R3_after_confirmations");
  await page.getByRole("button", { name: /자동 점검 실행|다시 점검/ }).click();
  await page.getByText("현재 설정된 점검 기준에서 확인된 문제가 없습니다.").first().waitFor();
  await shot("R4_ready_after_review");

  // Live upload of one scanned PDF into an empty business project.
  const wf = (await (await fetch(`${api}/workflows`)).json()).find((w) => w.name === "기업 제출서류 점검");
  const fresh = await (await fetch(`${api}/projects`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name: "[캡처] 라이브 업로드", workflow_id: wf.id }) })).json();
  await page.goto(`${web}/projects/${fresh.id}`, { waitUntil: "networkidle" });
  const scan = path.join(root, "evaluation/datasets/synthetic/test_variants/business/B01_all_valid/scanned/B01-3_납세증명서_스캔.pdf");
  await page.locator('input[type="file"]').setInputFiles(scan);
  await shot("U1_upload_selected", false);
  await page.getByRole("button", { name: /업로드|분석/ }).first().click();
  await page.waitForTimeout(3000);
  await shot("U2_upload_processing", false);
  await page.getByText("분석 완료").first().waitFor({ timeout: 120000 });
  await shot("U3_upload_done");
  for (const pid of [id, fresh.id]) await fetch(`${api}/projects/${pid}`, { method: "DELETE" });
}
console.log(overflow.length ? `HORIZONTAL OVERFLOW on: ${overflow.join(", ")}` : `no horizontal overflow at ${width}x${height}`);
await browser.close();
