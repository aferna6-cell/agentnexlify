/**
 * Journey 1 — Demo funnel (generic entry point)
 *
 * Critical path: /demo → dashboard lands, demo banner visible, DemoTour
 * coach-mark appears, banner CTA href contains /signup?from=demo.
 *
 * Safe for prod: demo routes only, read-only. No signups submitted.
 *
 * Run:
 *   PW_SKIP_WEBSERVER=1 npx playwright test \
 *     --config e2e/playwright.config.js \
 *     e2e/journeys/demo-funnel.spec.js
 */

// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Demo funnel — generic entry", () => {
  /**
   * Navigate to /demo and wait for the authenticated dashboard.
   * DemoLoginPage calls /api/v1/auth/demo-login, stores the JWT, then
   * redirects to /dashboard via React Router.
   */
  test("GET /demo lands on /dashboard", async ({ page }) => {
    await page.goto("/demo", { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

    // URL settled — we are past the redirect.
    expect(page.url()).toMatch(/\/dashboard/);
  });

  test("demo banner is visible after landing", async ({ page }) => {
    await page.goto("/demo", { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

    // DemoBanner renders when user.role === "demo" (decoded from JWT).
    const banner = page.getByTestId("demo-banner");
    await expect(banner).toBeVisible({ timeout: 15_000 });

    // Banner copy confirms "live demo" context.
    await expect(banner).toContainText(/live demo/i);
  });

  test("banner CTA href contains /signup?from=demo", async ({ page }) => {
    await page.goto("/demo", { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

    const cta = page
      .getByTestId("demo-banner")
      .getByRole("link", { name: /start your free account/i });

    await expect(cta).toBeVisible({ timeout: 10_000 });

    // Verify the href — the test NEVER clicks it (no signup submission).
    const href = await cta.getAttribute("href");
    expect(href).toContain("/signup?from=demo");
  });

  test("DemoTour coach-mark appears on first visit", async ({ page }) => {
    await page.goto("/demo", { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

    // DemoTour is mounted on the Agent OS page; it shows when:
    //   - user.role === "demo"
    //   - sessionStorage key "anx_demo_tour_done" is NOT set (fresh context)
    // A fresh page context guarantees a clean sessionStorage.
    const tourCard = page.getByTestId("demo-tour-card");
    await expect(tourCard).toBeVisible({ timeout: 15_000 });

    // Card has the correct ARIA role and is labelled as step 1.
    await expect(tourCard).toHaveAttribute("role", "dialog");
    await expect(tourCard).toHaveAttribute("aria-label", /Tour step 1 of 3/i);

    // Navigation controls are present.
    await expect(page.getByTestId("demo-tour-next")).toBeVisible();
    await expect(page.getByTestId("demo-tour-skip")).toBeVisible();
  });

  test("DemoTour can be dismissed with Skip", async ({ page }) => {
    await page.goto("/demo", { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

    const tourCard = page.getByTestId("demo-tour-card");
    await expect(tourCard).toBeVisible({ timeout: 15_000 });

    await page.getByTestId("demo-tour-skip").click();

    // After dismissal the card unmounts.
    await expect(tourCard).not.toBeVisible({ timeout: 5_000 });

    // Banner stays visible — dismiss only hides the tour, not the banner.
    await expect(page.getByTestId("demo-banner")).toBeVisible();
  });
});
