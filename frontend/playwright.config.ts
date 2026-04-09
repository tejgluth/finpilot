import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for FinPilot E2E tests.
 *
 * Prerequisites before running:
 *   - Backend must be running on port 8000 (uv run python -m backend.main)
 *   - The webServer block below starts the Vite dev server automatically
 *
 * Run: pnpm e2e
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [["html", { open: "never", outputFolder: "playwright-report" }], ["line"]]
    : "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "pnpm dev --host --port 5173",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    stdout: "ignore",
    stderr: "pipe",
  },
});
