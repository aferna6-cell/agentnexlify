/**
 * Journey 2 — Vertical demo passthrough
 *
 * Critical path: /demo?vertical=salon → banner CTA href contains
 * vertical=salon (JWT businessType passthrough). Proves the backend
 * encodes businessType into the demo JWT and DemoBanner reads it.
 *
 * Covers the "money path" because the vertical conversion funnel
 * (salon → salon onboarding) is how AgentNexLiFy earns higher-LTV
 * signups from vertical-specific ad campaigns.
 *
 * Safe for prod: demo routes only, read-only.
 *
 * Run:
 *   PW_SKIP_WEBSERVER=1 npx playwright test \
 *     --config e2e/playwright.config.js \
 *     e2e/journeys/demo-vertical.spec.js
 */

// @ts-check
const { test, expect } = require("@playwright/test");

// Live verticals per backend/routers/auth_demo.py _VERTICAL_RE.
const VERTICALS = ["salon", "plumbing", "financial_services"];

test.describe("Vertical demo — JWT businessType passthrough", () => {
  test("salon vertical: banner CTA href contains vertical=salon", async ({
    page,
  }) => {
    await page.goto("/demo?vertical=salon", { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

    const banner = page.getByTestId("demo-banner");
    await expect(banner).toBeVisible({ timeout: 15_000 });

    const cta = banner.getByRole("link", { name: /start your free account/i });
    await expect(cta).toBeVisible({ timeout: 10_000 });

    // DemoBanner builds the href as:
    //   /signup?from=demo&vertical=<encodeURIComponent(user.businessType)>
    // Must contain both "from=demo" and "vertical=salon".
    const href = await cta.getAttribute("href");
    expect(href, "CTA href missing from=demo param").toContain("from=demo");
    expect(
      href,
      `CTA href '${href}' missing vertical=salon — JWT businessType passthrough broken`,
    ).toContain("vertical=salon");
  });

  test("generic /demo (no vertical): banner CTA falls back to plumbing vertical", async ({
    page,
  }) => {
    await page.goto("/demo", { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

    const cta = page
      .getByTestId("demo-banner")
      .getByRole("link", { name: /start your free account/i });

    await expect(cta).toBeVisible({ timeout: 10_000 });

    const href = await cta.getAttribute("href");
    expect(href).toContain("from=demo");
    // Generic landing falls back to the plumbing demo tenant, whose JWT
    // businessType rides into the CTA (auth_demo.py _DEFAULT_VERTICAL).
    expect(
      href,
      "Generic demo CTA should carry the default plumbing vertical",
    ).toContain("vertical=plumbing");
  });

  // Spot-check two more verticals — proves the URL encoding survives the
  // API → JWT → React pipeline for each.
  for (const vertical of VERTICALS.slice(1)) {
    test(`${vertical} vertical: banner CTA href carries vertical=${vertical}`, async ({
      page,
    }) => {
      await page.goto(`/demo?vertical=${vertical}`, {
        waitUntil: "domcontentloaded",
      });
      await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

      const cta = page
        .getByTestId("demo-banner")
        .getByRole("link", { name: /start your free account/i });

      await expect(cta).toBeVisible({ timeout: 10_000 });
      const href = await cta.getAttribute("href");
      expect(href).toContain(`vertical=${vertical}`);
    });
  }
});
