import { defineConfig, devices } from "@playwright/test";

/**
 * Minimal Playwright setup for the core submission journey.
 *
 * It is deliberately not a full E2E platform: the backend runs the real OCR
 * pipeline, so the specs assert user-visible behaviour rather than internals.
 *
 * Environment:
 *   WEB_URL           default http://localhost:3000
 *   MENTOR_DIR        read-only mentor PDFs (never copied into the repository);
 *                     when unset the mentor journeys are skipped
 *   MENTOR_BUSINESS   default `${MENTOR_DIR}/패키지별/P001_정상`
 *   MENTOR_STUDENT    default `${MENTOR_DIR}/추가_학생서류_선택`
 */
const webUrl = process.env.WEB_URL ?? "http://localhost:3000";
export default defineConfig({
  testDir: "./e2e",
  timeout: 15 * 60 * 1000,
  // Document processing runs OCR synchronously inside the API request and
  // occupies its event loop, so unrelated reads can stall while a batch is
  // being analysed. Assertions therefore allow a long settle window instead of
  // masking the behaviour with retries.
  expect: { timeout: 180_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: webUrl,
    viewport: { width: 1440, height: 1000 },
    trace: "off",
    actionTimeout: 60_000,
    navigationTimeout: 60_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
