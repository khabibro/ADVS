import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { API, createScenarioProject, deleteProject, demoProjects, variantFile } from "./helpers";

/**
 * Applicant and reviewer flows through the real API and web app (start the demo first:
 * `scripts/demo reset`). Fresh submissions are created for anything that changes state, so the
 * pre-loaded demo projects stay as the presenter expects them.
 */
test.setTimeout(10 * 60 * 1000);
test.use({ viewport: { width: 1440, height: 900 } });

const banner = (page: Page) => page.locator('section[aria-labelledby="status-heading"]');

async function open(page: Page, id: string, hash = "") {
  await page.goto(`/projects/${id}${hash}`);
  await expect(banner(page)).toBeVisible();
}

test.describe("applicant flows", () => {
  test("D1: a correct submission is 제출 가능, and says it is not official approval", async ({ page, request }) => {
    const id = await createScenarioProject(request, "D1", "[E2E] D1");
    try {
      await open(page, id);
      await expect(banner(page).getByRole("heading", { name: "제출 가능" })).toBeVisible();
      await expect(banner(page)).toContainText("공식 승인 아님");
      await expect(page.getByText("제출됨 · 확인 완료")).toHaveCount(4);
      await expect(page.getByRole("heading", { name: "점검 결과" })).toHaveCount(0);
    } finally {
      await deleteProject(request, id);
    }
  });

  test("D2: an expired certificate is 보완 필요 and says which date and what to do", async ({ page, request }) => {
    const id = await createScenarioProject(request, "D2", "[E2E] D2");
    try {
      await open(page, id);
      await expect(banner(page).getByRole("heading", { name: "보완 필요" })).toBeVisible();
      await expect(banner(page)).toContainText("아래 1개 항목을 보완해 주세요.");
      const issues = page.locator('section[aria-labelledby="issues-heading"]');
      await expect(issues).toContainText("유효기간 종료일 2026. 08. 31. — 점검 기준일 2026. 10. 05.보다 이전입니다.");
      await expect(issues).toContainText("유효기간 내의 서류를 다시 발급받아 제출해 주세요.");
      await expect(issues.getByRole("link", { name: /근거 보기/ })).toBeVisible();
      const row = page.getByRole("heading", { name: "국세 납세증명서" }).locator("xpath=ancestor::li[1]");
      await expect(row).toContainText("보완 필요");
      await expect(row.getByRole("button", { name: /새 서류로 교체/ })).toBeVisible();
    } finally {
      await deleteProject(request, id);
    }
  });

  test("D5: a look-alike document is held for review, never 제출 가능", async ({ page, request }) => {
    const id = await createScenarioProject(request, "D5", "[E2E] D5");
    try {
      await open(page, id);
      await expect(banner(page).getByRole("heading", { name: "확인 필요" })).toBeVisible();
      await expect(banner(page).getByRole("heading", { name: "제출 가능" })).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "확인이 필요한 파일" })).toBeVisible();
      await expect(page.getByText(/서류 종류를 확인할 수 없습니다/).first()).toBeVisible();
      const row = page.getByRole("heading", { name: "국세 납세증명서" }).locator("xpath=ancestor::li[1]");
      await expect(row).toContainText("미제출");
    } finally {
      await deleteProject(request, id);
    }
  });

  test("D8: a missing document is marked in its row and can be uploaded right there", async ({ page, request }) => {
    const id = await createScenarioProject(request, "D8", "[E2E] D8");
    try {
      await open(page, id);
      await expect(banner(page).getByRole("heading", { name: "보완 필요" })).toBeVisible();
      const row = page.getByRole("heading", { name: "사업자등록증" }).locator("xpath=ancestor::li[1]");
      await expect(row).toContainText("미제출");
      await row.locator('input[type="file"]').setInputFiles(variantFile("business/B01_all_valid/digital/B01-1_사업자등록증.pdf"));
      // The check re-runs by itself once the file is analysed.
      await expect(banner(page).getByRole("heading", { name: "제출 가능" })).toBeVisible({ timeout: 60_000 });
      await expect(row).toContainText("제출됨 · 확인 완료");
    } finally {
      await deleteProject(request, id);
    }
  });

  test("a file the backend cannot read says what to do; an unsupported type is refused up front", async ({ page, request }) => {
    const id = await createScenarioProject(request, "D8", "[E2E] errors", { skipFirstFile: true });
    try {
      await open(page, id);
      const input = page.getByTestId("upload-input");
      await input.setInputFiles(variantFile("formats/F16_corrupt_files/F16a_사업자등록증_손상.pdf"));
      await expect(page.getByRole("alert").filter({ hasText: "파일을 열 수 없습니다" })).toContainText("원본에서 다시 저장하거나 스캔해서 올려 주세요");
      await expect(page.getByRole("button", { name: "다시 시도" })).toBeVisible();
      await input.setInputFiles({ name: "메모.txt", mimeType: "text/plain", buffer: Buffer.from("hello") });
      await expect(page.getByRole("status").filter({ hasText: "메모.txt: 지원하지 않는 파일 형식입니다" })).toBeVisible();
    } finally {
      await deleteProject(request, id);
    }
  });

  test("a photo (JPG) is accepted, like the backend accepts it", async ({ page, request }) => {
    const id = await createScenarioProject(request, "D8", "[E2E] photo", { skipFirstFile: true });
    try {
      await open(page, id);
      await page.getByTestId("upload-input").setInputFiles(variantFile("business/B01_all_valid/images/B01-1_사업자등록증_사진.jpg"));
      await expect(page.getByText(/1개 서류의 분석이 끝났습니다/)).toBeVisible({ timeout: 120_000 });
    } finally {
      await deleteProject(request, id);
    }
  });
});

test.describe("reviewer flow", () => {
  test("D6: confirm the values one by one with the keyboard; the status updates by itself", async ({ page, request }) => {
    const id = await createScenarioProject(request, "D6", "[E2E] D6");
    try {
      await open(page, id);
      await expect(banner(page).getByRole("heading", { name: "확인 필요" })).toBeVisible();
      await expect(banner(page)).toContainText("담당자 확인이 필요한 항목이 4개 있습니다.");
      await expect(page.getByRole("heading", { name: "확인할 항목 4개" })).toBeVisible();
      await expect(page.getByText("0 / 4 완료")).toBeVisible();
      // The original is shown next to every value.
      await expect(page.getByTestId("evidence-crop").first()).toBeVisible();

      const confirm = page.getByRole("button", { name: /원본과 같음/ });
      await confirm.first().focus();
      for (const remaining of [3, 2, 1]) {
        await page.keyboard.press("Enter");
        await expect(page.getByRole("heading", { name: `확인할 항목 ${remaining}개` })).toBeVisible();
      }
      await page.keyboard.press("Enter");
      // No "자동 점검 실행" click: the check re-runs and the banner changes.
      await expect(banner(page).getByRole("heading", { name: "제출 가능" })).toBeVisible({ timeout: 30_000 });
      await expect(banner(page)).toContainText("방금 확인 필요 → 제출 가능(으)로 바뀌었습니다");
      await expect(page.getByText("확인할 항목을 모두 처리했습니다 (4개 완료).")).toBeVisible();
    } finally {
      await deleteProject(request, id);
    }
  });

  test("D6: a value can be corrected instead of confirmed", async ({ page, request }) => {
    const id = await createScenarioProject(request, "D6", "[E2E] D6 correct");
    try {
      await open(page, id);
      await page.getByRole("button", { name: "값 수정" }).first().click();
      await page.getByLabel(/올바른 값을 입력/).fill("2027-03-30");
      await page.keyboard.press("Enter");
      await expect(page.getByRole("heading", { name: "확인할 항목 3개" })).toBeVisible();
      await expect(page.getByText("1 / 4 완료")).toBeVisible();
    } finally {
      await deleteProject(request, id);
    }
  });
});

test.describe("every screen shows exactly what the API decided", () => {
  const LABEL = { READY: "제출 가능", REVIEW_REQUIRED: "확인 필요", NEEDS_CORRECTION: "보완 필요" } as const;
  const ROW = {
    OK: "제출됨 · 확인 완료",
    NEEDS_CORRECTION: "보완 필요",
    REVIEW_REQUIRED: "확인 필요",
    MISSING: "미제출",
    PROCESSING: "분석 중",
    FAILED: "분석 실패",
    NOT_CHECKED: "분석 완료 · 점검 대기",
  } as const;

  test("D1-D8: banner, count, rows and issues equal the overview response", async ({ page, request }) => {
    const projects = await demoProjects(request);
    expect(projects.length).toBe(8);
    for (const project of projects) {
      const overview = await (await request.get(`${API}/projects/${project.id}/overview`)).json();
      await open(page, project.id);
      const b = banner(page);
      expect(overview.status, project.name).toBeTruthy();
      await expect(b.getByRole("heading", { name: LABEL[overview.status as keyof typeof LABEL] }), project.name).toBeVisible();
      if (overview.status === "NEEDS_CORRECTION") await expect(b).toContainText(`아래 ${overview.status_item_count}개 항목을 보완해 주세요.`);
      if (overview.status === "REVIEW_REQUIRED") await expect(b).toContainText(`담당자 확인이 필요한 항목이 ${overview.status_item_count}개 있습니다.`);
      for (const requirement of overview.requirements) {
        const row = page.getByRole("heading", { name: requirement.display_name, exact: true }).locator("xpath=ancestor::li[1]");
        await expect(row, `${project.name} ${requirement.display_name}`).toContainText(ROW[requirement.state as keyof typeof ROW]);
      }
      const listed = overview.issues.filter(
        (i: { code: string }) => !["OCR_UNCERTAIN", "REQUIRED_FIELD_UNRESOLVED", "BUSINESS_NUMBER_CHECKSUM_FAILED"].includes(i.code),
      );
      const heading = page.getByRole("heading", { name: /^(보완할|확인할) 항목 \d+개$/ });
      if (listed.length === 0) {
        await expect(page.locator('section[aria-labelledby="issues-heading"]')).toHaveCount(0);
      } else {
        const counts = await heading.allTextContents();
        const shown = counts.filter((t) => /^(보완할|확인할) 항목/.test(t) && !t.startsWith("확인할 항목 " + overview.counts.review_open + "개")).reduce((n, t) => n + Number(t.match(/\d+/)![0]), 0);
        expect(shown, project.name).toBeGreaterThanOrEqual(listed.length);
      }
      if (overview.counts.review_open > 0) await expect(page.getByRole("heading", { name: `확인할 항목 ${overview.counts.review_open}개` })).toBeVisible();
    }
  });

  test("no raw enum, stack trace or 'undefined' is shown on any demo screen", async ({ page, request }) => {
    const raw = /\b(READY|REVIEW_REQUIRED|NEEDS_CORRECTION|MISSING_REQUIRED_DOCUMENT|OCR_UNCERTAIN|UNKNOWN|undefined|NaN|\[object Object\]|Traceback)\b/;
    for (const project of await demoProjects(request)) {
      await open(page, project.id);
      expect(await page.locator("body").innerText(), project.name).not.toMatch(raw);
    }
  });

  test("the list shows the same status as each submission screen", async ({ page, request }) => {
    const summaries: Array<{ project_id: string; status: string; status_item_count: number }> = await (await request.get(`${API}/project-summaries`)).json();
    const demo = await demoProjects(request);
    await page.goto("/projects");
    for (const project of demo) {
      const summary = summaries.find((s) => s.project_id === project.id)!;
      const card = page.getByRole("heading", { name: project.name, exact: true }).locator("xpath=ancestor::a[1]");
      await expect(card).toContainText(LABEL[summary.status as keyof typeof LABEL]);
    }
  });
});

test.describe("accessibility (axe: no serious or critical violations)", () => {
  async function violations(page: Page) {
    const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    return result.violations
      .filter((v) => v.impact === "serious" || v.impact === "critical")
      .map((v) => `${v.id}: ${v.help} (${v.nodes.length} nodes) e.g. ${v.nodes[0]?.html.slice(0, 120)}`);
  }

  test("list, new submission, submission screens and document detail", async ({ page, request }) => {
    const demo = await demoProjects(request);
    const byName = (code: string) => demo.find((p) => p.name.startsWith(code))!;
    const targets = ["/projects", "/projects/new", `/projects/${byName("D1").id}`, `/projects/${byName("D2").id}`, `/projects/${byName("D5").id}`, `/projects/${byName("D6").id}`];
    const docs: Array<{ id: string }> = await (await request.get(`${API}/projects/${byName("D6").id}/documents`)).json();
    targets.push(`/projects/${byName("D6").id}/documents/${docs[0].id}`);
    for (const target of targets) {
      await page.goto(target);
      await page.waitForLoadState("networkidle");
      expect(await violations(page), target).toEqual([]);
    }
  });

  test("the same screens at phone width: no horizontal scroll and no violations", async ({ page, request }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const demo = await demoProjects(request);
    for (const target of ["/projects", `/projects/${demo.find((p) => p.name.startsWith("D6"))!.id}`, `/projects/${demo.find((p) => p.name.startsWith("D2"))!.id}`]) {
      await page.goto(target);
      await page.waitForLoadState("networkidle");
      const wide = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
      expect(wide, `${target} scrolls horizontally`).toBe(false);
      expect(await violations(page), target).toEqual([]);
    }
  });
});

test.describe("projector sizes", () => {
  for (const [width, height] of [[1280, 720], [1920, 1080]] as const) {
    test(`${width}x${height}: no horizontal scroll on the demo screens`, async ({ page, request }) => {
      await page.setViewportSize({ width, height });
      for (const project of await demoProjects(request)) {
        await open(page, project.id);
        const wide = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
        expect(wide, `${project.name} at ${width}`).toBe(false);
      }
    });
  }
});
