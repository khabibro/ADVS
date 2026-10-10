// Capture screenshots of the demo screens with Playwright (Chromium).
//   node scripts/demo_screenshots.mjs <outDir> [width] [height]
// Env: WEB_URL (default http://localhost:3000), API_URL (default http://localhost:8000/api/v1)
import { createRequire } from "node:module";
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
const shot = async (name, fullPage = true) => {
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage });
  console.log("saved", name);
};

await page.goto(`${web}/projects`, { waitUntil: "networkidle" });
await shot("00_projects_list");
for (const [code, project] of Object.entries(byCode)) {
  await page.goto(`${web}/projects/${project.id}`, { waitUntil: "networkidle" });
  await shot(`${code}_workspace`);
}
await browser.close();
