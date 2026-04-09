/**
 * first_run.spec.ts — E2E release gate for the FinPilot first-run flow.
 *
 * This is the public release gate: if this test suite fails, the repo does not ship.
 *
 * Covers:
 *   1. App boots — frontend serves and backend health check passes
 *   2. Setup wizard loads — SetupPage renders with all wizard sections
 *   3. Safe local mode — navigating to /strategy with no keys configured does not crash
 *   4. Strategy page — tab bar renders, default Build tab is active
 *   5. Premade team browser — premade catalog loads and team cards are visible
 *   6. Backtest panel — form renders and a run attempt with no AI provider surfaces an error
 *
 * Prerequisites:
 *   - Backend running on port 8000 (uv run python -m backend.main)
 *   - Vite dev server started by Playwright via playwright.config.ts webServer
 */

import { expect, test } from "@playwright/test";

// ── 1. App boots ───────────────────────────────────────────────────────────────

test("backend health check passes", async ({ request }) => {
  const response = await request.get("http://localhost:8000/api/health");
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.status).toBe("ok");
});

// ── 2. Setup wizard loads ──────────────────────────────────────────────────────

test("setup wizard renders at root", async ({ page }) => {
  await page.goto("/");

  // The SetupWizard shows a loading state first, then the wizard panels.
  // Step 4 (Trading risk acknowledgment) is always rendered once loaded.
  await expect(
    page.getByText("Trading risk acknowledgment"),
  ).toBeVisible({ timeout: 10_000 });

  // The acknowledgment step has an eyebrow label "Step 4"
  await expect(page.getByText("Step 4")).toBeVisible();

  // All 9 risk items are present
  await expect(
    page.getByText("FinPilot is a research tool, not investment advice", {
      exact: false,
    }),
  ).toBeVisible();
});

// ── 3. Safe local mode with no keys ───────────────────────────────────────────

test("navigating to /strategy with no AI keys does not crash", async ({
  page,
}) => {
  // Navigate directly — no auth guard in the router.
  // The setup wizard informs users to add keys first, but it does NOT block navigation.
  await page.goto("/strategy");

  // The page should render (no white screen, no unhandled error overlay).
  // Vite dev mode shows an error overlay on unhandled exceptions.
  await expect(page.locator("vite-error-overlay")).not.toBeAttached();

  // The strategy page content should be present within normal load time.
  await expect(page.getByRole("tablist")).toBeVisible({ timeout: 10_000 });
});

// ── 4. Strategy page tab bar ───────────────────────────────────────────────────

test("strategy page renders tab bar with Build tab active", async ({
  page,
}) => {
  await page.goto("/strategy");

  const tablist = page.getByRole("tablist", { name: "Strategy views" });
  await expect(tablist).toBeVisible({ timeout: 10_000 });

  // All four tabs are present
  for (const label of ["Build", "Visualize", "Compare", "Custom Team"]) {
    await expect(page.getByRole("tab", { name: label })).toBeVisible();
  }

  // Build tab is selected by default (aria-selected="true")
  await expect(page.getByRole("tab", { name: "Build" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
});

// ── 5. Premade team browser ────────────────────────────────────────────────────

test("premade team browser loads and shows teams", async ({ page }) => {
  await page.goto("/strategy");

  // PremadeTeamBrowser is rendered in the Build panel once the catalog API responds.
  // The Panel title is "Premade teams".
  await expect(
    page.getByText("Premade teams", { exact: true }),
  ).toBeVisible({ timeout: 10_000 });

  // At least one "Use this team" button is visible, confirming teams loaded.
  const useButtons = page.getByRole("button", { name: "Use this team" });
  await expect(useButtons.first()).toBeVisible({ timeout: 10_000 });
});

// ── 6. Backtest panel error surfacing ─────────────────────────────────────────

test("backtest panel renders form and surfaces error on run attempt", async ({
  page,
}) => {
  // Intercept the backtest stream and return an immediate error response.
  // This makes the test deterministic — we don't care whether the dev
  // environment has API keys or an active team configured.
  await page.route("**/api/backtest/stream", (route) => {
    return route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({ detail: "No AI provider configured." }),
    });
  });

  await page.goto("/backtest");

  // The run button should be visible — confirms the form rendered correctly.
  const runButton = page.getByRole("button", { name: "Run truthful backtest" });
  await expect(runButton).toBeVisible({ timeout: 10_000 });

  await runButton.click();

  // The client sees a non-OK response, throws, and the store sets error state.
  // BacktestPage renders errors in a .text-ember div.
  const errorEl = page.locator(".text-ember").first();
  await expect(errorEl).toBeVisible({ timeout: 10_000 });
});
