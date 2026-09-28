import { expect, test, type Page } from "@playwright/test";

/**
 * Mentor PDFs are read-only material held outside the repository, so the specs
 * take their location from the environment and skip when it is absent. Nothing
 * here ever copies a mentor PDF into the repository.
 */
const MENTOR_ROOT = process.env.MENTOR_DIR;
const BUSINESS = {
  business: process.env.MENTOR_BUSINESS ?? `${MENTOR_ROOT}/패키지별/P001_정상`,
  student: process.env.MENTOR_STUDENT ?? `${MENTOR_ROOT}/추가_학생서류_선택`,
};

const EVALUATION_DATE = "2026-09-19";

test.skip(
  !MENTOR_ROOT && !process.env.MENTOR_BUSINESS,
  "MENTOR_DIR is not set; skipping read-only mentor PDF journeys",
);

const BACKEND_ENUMS = [
  "UPLOADED",
  "PREPROCESSING",
  "OCR_PENDING",
  "OCR_PROCESSING",
  "OCR_COMPLETED",
  "CLASSIFYING",
  "EXTRACTING",
  "VALIDATING",
  "COMPLETED",
  "FAILED",
  "READY",
  "REVIEW_REQUIRED",
  "NEEDS_CORRECTION",
  "UNKNOWN",
  "SUFFICIENT",
  "UNAVAILABLE",
  "HUMAN_CONFIRMED",
  "HUMAN_CORRECTED",
  "MACHINE",
  "CONFIRMED",
  "CORRECTED",
  "REJECTED",
  "CANNOT_DETERMINE",
  "PENDING",
  "EXPIRED_DOCUMENT",
  "INFORMATION_MISMATCH",
  "MISSING_REQUIRED_DOCUMENT",
  "OCR_UNCERTAIN",
  "REQUIRED_FIELD_UNRESOLVED",
  "RULE_CONDITION_NOT_MET",
];

async function createProject(page: Page, workflow: RegExp, name: string) {
  await page.goto("/projects/new");
  await page.locator(`label:has-text("${workflow.source}")`).first().click();
  await page.getByLabel(/제출 건 이름/).fill(name);
  await page.getByRole("button", { name: "제출 건 만들기" }).click();
  await page.waitForURL(/\/projects\/[0-9a-f-]{36}$/);
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: /^필수 서류/ })).toBeVisible();
  return page.url().split("/").pop()!;
}

async function uploadMany(page: Page, files: string[]) {
  await page.locator("input[type=file]").setInputFiles(files);
  await expect(page.getByTestId("upload-submit")).toBeVisible();
  await page.getByTestId("upload-submit").click();
  await expect(page.getByTestId("upload-submit")).toHaveCount(0, {
    timeout: 14 * 60 * 1000,
  });
}

test.describe("ADVS submission journey", () => {
  test("four PDFs in one selection upload once, map to requirements, and survive a hard refresh", async ({
    page,
  }) => {
    const projectId = await createProject(
      page,
      /기업 제출서류 점검/,
      "E2E 다중 업로드",
    );
    await expect(page.getByText("필수 0 / 4")).toBeVisible();

    const input = page.locator("input[type=file]");
    await expect(input).toHaveAttribute("multiple", "");
    await expect(input).toHaveAttribute("accept", /pdf/);

    const requests: string[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.pathname.endsWith("/documents") && request.method() === "POST") {
        requests.push(url.pathname);
      }
    });

    const files = [
      `${BUSINESS.business}/P001_사업자등록증.pdf`,
      `${BUSINESS.business}/P001_중소기업확인서.pdf`,
      `${BUSINESS.business}/P001_국세 납세증명서.pdf`,
      `${BUSINESS.business}/P001_4대 사회보험료 완납증명서.pdf`,
    ];
    await input.setInputFiles(files);
    await expect(page.getByTestId("upload-submit")).toHaveText(
      "4개 파일 업로드",
    );
    await page.getByTestId("upload-submit").click();

    // The action must lock immediately and resist repeated activation.
    const submit = page.getByTestId("upload-submit");
    await expect(submit).toHaveText("업로드 중...");
    await expect(submit).toBeDisabled();
    for (let i = 0; i < 5; i += 1) {
      await submit
        .click({ force: true, noWaitAfter: true })
        .catch(() => undefined);
    }
    await expect(page.getByTestId("upload-submit")).toHaveCount(0, {
      timeout: 14 * 60 * 1000,
    });

    expect(requests).toHaveLength(4);
    await expect(page.getByText("필수 4 / 4")).toBeVisible({ timeout: 60_000 });
    for (const name of [
      "사업자등록증",
      "중소기업확인서",
      "국세 납세증명서",
      "4대 사회보험료 완납증명서",
    ]) {
      await expect(
        page.getByRole("heading", { name, exact: true }),
      ).toBeVisible();
    }

    const beforeRefresh = await page.locator("main").innerText();
    await page.reload();
    await expect(page.getByText("필수 4 / 4")).toBeVisible();
    const afterRefresh = await page.locator("main").innerText();
    expect(afterRefresh).not.toContain("알 수 없는 문서");
    expect(afterRefresh).toContain("분석 완료");
    for (const token of BACKEND_ENUMS) {
      expect(beforeRefresh).not.toContain(token);
      expect(afterRefresh).not.toContain(token);
    }

    // Automatic verification with an explicit evaluation date.
    await page.getByLabel("점검 기준일").fill(EVALUATION_DATE);
    await page.getByRole("button", { name: /자동 점검 실행/ }).click();
    await expect(page.getByText("제출 가능").first()).toBeVisible();
    await expect(
      page.getByText(
        /공식 승인, 법적 검증 또는 기관의 접수 결정을 대신하지 않습니다/,
      ),
    ).toBeVisible();
    expect(projectId).toBeTruthy();
  });

  test("a normal business package verifies as 제출 가능", async ({ page }) => {
    await createProject(page, /기업 제출서류 점검/, "E2E P001 정상");
    await uploadMany(page, [
      `${BUSINESS.business}/P001_사업자등록증.pdf`,
      `${BUSINESS.business}/P001_중소기업확인서.pdf`,
      `${BUSINESS.business}/P001_국세 납세증명서.pdf`,
      `${BUSINESS.business}/P001_4대 사회보험료 완납증명서.pdf`,
    ]);
    await page.getByLabel("점검 기준일").fill(EVALUATION_DATE);
    await page.getByRole("button", { name: /자동 점검 실행/ }).click();
    await expect(page.getByText("제출 가능").first()).toBeVisible();
  });

  test("replacing a document makes the previous result stale and re-verification updates it", async ({
    page,
  }) => {
    await createProject(page, /기업 제출서류 점검/, "E2E 교체");
    await uploadMany(page, [
      `${BUSINESS.business}/P001_사업자등록증.pdf`,
      `${BUSINESS.business}/P001_중소기업확인서.pdf`,
      `${BUSINESS.business}/P001_국세 납세증명서.pdf`,
      `${BUSINESS.business}/P001_4대 사회보험료 완납증명서.pdf`,
    ]);
    await page.getByLabel("점검 기준일").fill(EVALUATION_DATE);
    await page.getByRole("button", { name: /자동 점검 실행/ }).click();
    await expect(page.getByText("제출 가능").first()).toBeVisible();

    // Replace one document from its requirement slot.
    await page.getByRole("button", { name: "새 서류로 교체" }).first().click();
    await page
      .locator("input[type=file]")
      .setInputFiles(`${BUSINESS.business}/P001_중소기업확인서.pdf`);
    await page.getByTestId("upload-submit").click();
    await expect(page.getByTestId("upload-submit")).toHaveCount(0, {
      timeout: 14 * 60 * 1000,
    });

    // The old READY must stop being authoritative.
    await expect(page.getByText("변경된 내용이 있습니다.")).toBeVisible();
    await expect(
      page.getByText(/현재 설정된 점검 기준에서 확인된 문제가 없습니다/),
    ).toHaveCount(0);

    await page.getByRole("button", { name: /다시 점검/ }).click();
    await expect(page.getByText("제출 가능").first()).toBeVisible();
  });

  test("OCR-uncertain fields open a review queue that updates the result", async ({
    page,
  }) => {
    await createProject(page, /기업 제출서류 점검/, "E2E 검토 필요");
    await uploadMany(page, [
      `${BUSINESS.business}/P007_사업자등록증.pdf`,
      `${BUSINESS.business}/P007_중소기업확인서.pdf`,
      `${BUSINESS.business}/P007_국세 납세증명서.pdf`,
      `${BUSINESS.business}/P007_4대 사회보험료 완납증명서.pdf`,
    ]);
    await page.getByLabel("점검 기준일").fill(EVALUATION_DATE);
    await page.getByRole("button", { name: /자동 점검 실행/ }).click();
    await expect(page.getByText("확인 필요").first()).toBeVisible();

    const confirm = page.getByRole("button", { name: "확인하기" }).first();
    await expect(confirm).toBeVisible();
    await confirm.click();
    await expect(
      page.getByText("인식 신뢰도가 자동 사용 기준보다 낮습니다."),
    ).toBeVisible();
    await page.getByRole("button", { name: "검토 저장" }).click();
    await expect(page.getByText("변경된 내용이 있습니다.")).toBeVisible();

    await page.getByRole("button", { name: /다시 점검/ }).click();
    await expect(page.getByText("확인 필요").first()).toBeVisible();
  });

  test("an optional missing transcript is not treated as an error", async ({
    page,
  }) => {
    await createProject(page, /학생 제출서류 점검/, "E2E 학생 선택 서류 없음");
    await expect(page.getByText("성적증명서")).toBeVisible();
    await uploadMany(page, [`${BUSINESS.student}/재학증명서_정상.pdf`]);
    await expect(page.getByText("필수 1 / 1")).toBeVisible();
    await page.getByLabel("점검 기준일").fill(EVALUATION_DATE);
    await page.getByRole("button", { name: /자동 점검 실행/ }).click();
    const body = await page.locator("main").innerText();
    // The optional requirement must not produce a missing-document issue.
    expect(body).not.toContain("필수 서류가 누락되었습니다.");
    for (const token of BACKEND_ENUMS) {
      expect(body).not.toContain(token);
    }
  });

  test("an expired document surfaces 보완 필요 with an actionable issue", async ({
    page,
  }) => {
    await createProject(page, /기업 제출서류 점검/, "E2E 유효기간 만료");
    await uploadMany(page, [
      `${BUSINESS.business}/P004_사업자등록증.pdf`,
      `${BUSINESS.business}/P004_중소기업확인서.pdf`,
      `${BUSINESS.business}/P004_국세 납세증명서.pdf`,
      `${BUSINESS.business}/P004_4대 사회보험료 완납증명서.pdf`,
    ]);
    await page.getByLabel("점검 기준일").fill(EVALUATION_DATE);
    await page.getByRole("button", { name: /자동 점검 실행/ }).click();
    await expect(page.getByText("보완 필요").first()).toBeVisible();
    await expect(page.getByText("유효기간이 만료되었습니다.")).toBeVisible();
    await expect(
      page.getByRole("link", { name: /새 서류로 교체/ }).first(),
    ).toBeVisible();
  });

  test("the layout has no horizontal overflow and stays usable on mobile", async ({
    page,
  }) => {
    await createProject(page, /기업 제출서류 점검/, "E2E 반응형");
    for (const width of [1440, 1024, 768, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.reload();
      await expect(page.getByRole("heading", { name: /^필수 서류/ })).toBeVisible();
      const metrics = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 1);
    }
  });
});
