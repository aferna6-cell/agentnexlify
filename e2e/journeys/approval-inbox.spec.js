/**
 * Journey 3 — Approval inbox (Agent OS)
 *
 * Critical path: from a demo session → navigate to /dashboard/agent-os →
 * page renders. Seeded demo data should show threads + a pending draft.
 * Nightly reseed timing can mean the inbox is empty; we tolerate that with
 * soft assertions (test.info warnings) rather than hard failures.
 *
 * The "money path" aspect: the approval inbox is the moment a business
 * owner sees AI-drafted outbound communications before they send — the core
 * value proposition of AgentNexLiFy.
 *
 * Safe for prod: demo session only, read-only. No approvals submitted.
 *
 * Run:
 *   PW_SKIP_WEBSERVER=1 npx playwright test \
 *     --config e2e/playwright.config.js \
 *     e2e/journeys/approval-inbox.spec.js
 */

// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Agent OS approval inbox — demo session", () => {
  /**
   * Shared setup: land a demo session and navigate to the Agent OS inbox.
   * The /demo route logs us in and redirects to /dashboard which (per
   * App.jsx pageFromPath logic) defaults to agent_os. Direct navigation to
   * /dashboard/agent-os also works.
   */
  test.beforeEach(async ({ page }) => {
    await page.goto("/demo", { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

    // Explicit navigation to the Agent OS inbox URL.
    await page.goto("/dashboard/agent-os", { waitUntil: "domcontentloaded" });

    // Wait for the React lazy bundle to load — SkeletonLoader or content.
    await page.waitForLoadState("networkidle", { timeout: 20_000 });
  });

  test("Agent OS page renders without error", async ({ page }) => {
    // Verify we are on the right path.
    expect(page.url()).toMatch(/\/dashboard\/agent-os|\/dashboard/);

    // There must be no top-level JS crash (PageErrorBoundary "Something went
    // wrong" renders only on unhandled errors).
    await expect(
      page.getByText("Something went wrong"),
    ).not.toBeVisible({ timeout: 5_000 });

    // The demo banner is still present — session is intact.
    await expect(page.getByTestId("demo-banner")).toBeVisible({ timeout: 10_000 });
  });

  test("inbox thread rail renders (data-tour target exists)", async ({
    page,
  }) => {
    // DemoTour targets [data-tour="thread-rail"]. Its existence proves the
    // Agent OS shell component mounted correctly regardless of data state.
    await expect(
      page.locator('[data-tour="thread-rail"]'),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("deliverable panel target is in the DOM", async ({ page }) => {
    // The deliverable panel may be hidden until a thread is selected, but
    // the container should exist in the DOM after mount.
    const panel = page.locator('[data-tour="deliverable-panel"]');
    const exists = await panel.count();

    if (exists === 0) {
      // Soft — panel may not render when inbox is empty (reseed timing).
      test.info().annotations.push({
        type: "warning",
        description:
          "data-tour=deliverable-panel not in DOM — inbox may be empty (nightly reseed timing). Skipping assertion.",
      });
    } else {
      // Panel is present — verify it is attached to the document.
      await expect(panel.first()).toBeAttached();
    }
  });

  test("pending draft exists OR graceful empty state visible (soft)", async ({
    page,
  }) => {
    // The seeded demo tenant has a pending approval draft waiting. After the
    // nightly reset window (3–6 AM UTC) the seed job should have run. If the
    // inbox is empty we log a warning rather than fail — reseed timing.

    // Check for the approve button region (present when a draft is selected).
    const approveRegion = page.locator('[data-tour="approve-button"]');
    const threadItems = page.locator('[data-tour="thread-rail"] [role="listitem"], [data-tour="thread-rail"] li');

    // Wait briefly for async data to settle.
    await page.waitForTimeout(3_000);

    const threadCount = await threadItems.count();

    if (threadCount === 0) {
      test.info().annotations.push({
        type: "warning",
        description:
          `Inbox is empty (0 thread items). Nightly reseed may not have run yet (${new Date().toISOString()}). This is a soft warning, not a test failure.`,
      });
      // Still assert no crash.
      await expect(
        page.getByText("Something went wrong"),
      ).not.toBeVisible();
    } else {
      // Data is present — click the first thread and verify the deliverable
      // panel appears with the approve target.
      await threadItems.first().click();
      await expect(
        page.locator('[data-tour="approve-button"]').or(
          page.locator('[data-tour="deliverable-panel"]'),
        ).first(),
      ).toBeVisible({ timeout: 10_000 });

      test.info().annotations.push({
        type: "info",
        description: `Inbox has ${threadCount} thread(s). Approval workflow UI visible.`,
      });
    }
  });
});
