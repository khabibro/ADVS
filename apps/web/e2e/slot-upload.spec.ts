import { expect, test, type Locator, type Page } from "@playwright/test";
import { createEmptyProject, deleteProject, variantFile } from "./helpers";

/**
 * The per-slot "업로드" buttons and the drop zone, driven like a person does (a real file chooser, not
 * setInputFiles on the hidden input). Regression test for the slot buttons that did nothing. Fictional
 * TEST SAMPLE files only. Start the demo first: `scripts/demo reset`.
 */
test.setTimeout(5 * 60 * 1000);

const BUSINESS = "기업 제출서류 점검";
const STUDENT = "학생 제출서류 점검";
const B1 = "business/B01_all_valid/digital/B01-1_사업자등록증.pdf";
const B2 = "business/B01_all_valid/digital/B01-2_중소기업확인서.pdf";
const S1 = "student/S01_all_valid/digital/S01-1_재학증명서.pdf";
const S2 = "student/S01_all_valid/digital/S01-2_성적증명서.pdf";

const rowOf = (page: Page, name: string) =>
  page.getByRole("heading", { name }).locator("xpath=ancestor::li[1]");
const slotButton = (page: Page, name: string) =>
  page.getByRole("button", { name: `${name} 업로드` });

async function openProject(
  page: Page,
  request: Parameters<typeof createEmptyProject>[0],
  workflow: string,
  title: string,
) {
  const id = await createEmptyProject(request, workflow, title);
  await page.goto(`/projects/${id}`);
  await expect(page.getByRole("heading", { name: "제출 서류" })).toBeVisible();
  return id;
}

/** Click (or run `activate`) and answer the file chooser that must open. */
async function chooseFile(
  page: Page,
  activate: () => Promise<void>,
  rel: string,
) {
  const [chooser] = await Promise.all([
    page.waitForEvent("filechooser", { timeout: 15_000 }),
    activate(),
  ]);
  await chooser.setFiles(variantFile(rel));
  return chooser;
}

test.describe("slot upload buttons open a file chooser and upload to that slot", () => {
  test("business: a required slot", async ({ page, request }) => {
    const id = await openProject(
      page,
      request,
      BUSINESS,
      "[E2E] slot business",
    );
    try {
      const row = rowOf(page, "사업자등록증");
      await expect(row).toContainText("미제출");
      await chooseFile(
        page,
        () => slotButton(page, "사업자등록증").click(),
        B1,
      );
      await expect(row).toContainText("제출됨 · 확인 완료", {
        timeout: 120_000,
      });
    } finally {
      await deleteProject(request, id);
    }
  });

  test("student: the required slot (재학증명서) and the optional slot (성적증명서)", async ({
    page,
    request,
  }) => {
    const id = await openProject(page, request, STUDENT, "[E2E] slot student");
    try {
      await chooseFile(page, () => slotButton(page, "재학증명서").click(), S1);
      await expect(rowOf(page, "재학증명서")).toContainText(
        "제출됨 · 확인 완료",
        { timeout: 120_000 },
      );
      await expect(rowOf(page, "성적증명서")).toContainText("미제출");
      await chooseFile(page, () => slotButton(page, "성적증명서").click(), S2);
      await expect(rowOf(page, "성적증명서")).toContainText(
        "제출됨 · 확인 완료",
        { timeout: 120_000 },
      );
    } finally {
      await deleteProject(request, id);
    }
  });

  test("a different document than the slot says shows the existing mismatch message", async ({
    page,
    request,
  }) => {
    const id = await openProject(
      page,
      request,
      BUSINESS,
      "[E2E] slot mismatch",
    );
    try {
      await chooseFile(
        page,
        () => slotButton(page, "사업자등록증").click(),
        B2,
      );
      await expect(
        page.getByText(
          /사업자등록증 칸에 올린 파일은 중소기업확인서\(으\)로 인식/,
        ),
      ).toBeVisible({ timeout: 120_000 });
    } finally {
      await deleteProject(request, id);
    }
  });

  test("keyboard: Enter and Space on the focused slot button each open the chooser", async ({
    page,
    request,
  }) => {
    const id = await openProject(page, request, STUDENT, "[E2E] slot keyboard");
    try {
      const button = slotButton(page, "성적증명서");
      await button.focus();
      for (const key of ["Enter", "Space"]) {
        const [chooser] = await Promise.all([
          page.waitForEvent("filechooser", { timeout: 15_000 }),
          page.keyboard.press(key),
        ]);
        expect(chooser.isMultiple()).toBe(false);
      }
      // The slot's own hidden input is not a tab stop; the button is the only control.
      await expect(
        rowOf(page, "성적증명서").locator('input[type="file"]'),
      ).toHaveAttribute("tabindex", "-1");
    } finally {
      await deleteProject(request, id);
    }
  });

  test("the same file can be chosen again for the same slot", async ({
    page,
    request,
  }) => {
    const id = await openProject(
      page,
      request,
      BUSINESS,
      "[E2E] slot same file",
    );
    try {
      const posts: string[] = [];
      page.on("request", (r) => {
        if (
          r.method() === "POST" &&
          /\/projects\/[^/]+\/documents$/.test(r.url())
        )
          posts.push(r.url());
      });
      // A different document than the slot says leaves the slot open, so the same button is used twice.
      await chooseFile(
        page,
        () => slotButton(page, "사업자등록증").click(),
        B2,
      );
      await expect.poll(() => posts.length, { timeout: 60_000 }).toBe(1);
      // Choosing the very same file again must still reach the app (the input is reset after every pick):
      // the upload queue answers with its duplicate notice instead of silently ignoring the pick.
      await chooseFile(
        page,
        () => slotButton(page, "사업자등록증").click(),
        B2,
      );
      await expect(
        page.getByText("이미 목록에 있는 파일 1개는 중복으로 제외했습니다."),
      ).toBeVisible();
      expect(posts).toHaveLength(1);
      await expect(
        rowOf(page, "사업자등록증").locator('input[type="file"]'),
      ).toHaveValue("");
    } finally {
      await deleteProject(request, id);
    }
  });
});

test.describe("the 서류 추가 drop zone", () => {
  test("click opens the chooser (several files allowed) and the file is analysed", async ({
    page,
    request,
  }) => {
    const id = await openProject(
      page,
      request,
      BUSINESS,
      "[E2E] dropzone click",
    );
    try {
      const [chooser] = await Promise.all([
        page.waitForEvent("filechooser", { timeout: 15_000 }),
        page.getByText("서류 파일을 끌어다 놓거나 선택해 주세요").click(),
      ]);
      expect(chooser.isMultiple()).toBe(true);
      await chooser.setFiles(variantFile(B1));
      await expect(rowOf(page, "사업자등록증")).toContainText(
        "제출됨 · 확인 완료",
        { timeout: 120_000 },
      );
    } finally {
      await deleteProject(request, id);
    }
  });

  test("drag and drop of a file is analysed", async ({ page, request }) => {
    const id = await openProject(
      page,
      request,
      BUSINESS,
      "[E2E] dropzone drop",
    );
    try {
      const zone: Locator = page
        .locator("label")
        .filter({ hasText: "서류 파일을 끌어다 놓거나 선택해 주세요" });
      const fs = await import("node:fs");
      const bytes = [...fs.readFileSync(variantFile(B1))];
      const dataTransfer = await page.evaluateHandle((data) => {
        const dt = new DataTransfer();
        dt.items.add(
          new File([new Uint8Array(data)], "B01-1_사업자등록증.pdf", {
            type: "application/pdf",
          }),
        );
        return dt;
      }, bytes);
      await zone.dispatchEvent("dragover", { dataTransfer });
      await zone.dispatchEvent("drop", { dataTransfer });
      await expect(rowOf(page, "사업자등록증")).toContainText(
        "제출됨 · 확인 완료",
        { timeout: 120_000 },
      );
    } finally {
      await deleteProject(request, id);
    }
  });
});
