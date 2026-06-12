/**
 * Daily production smoke for the public live-demo sandbox — the front door.
 *
 * Runs on the e2e schedule (after the 3-6 AM UTC self-seed window) with NO
 * secrets: demo-login is a public endpoint. Two layers:
 *   1. API: demo-login issues a token for the seeded demo tenant.
 *   2. Browser: /demo logs a visitor in and lands them in the dashboard
 *      with the demo banner visible.
 *
 * A 404 "Demo is not set up yet" is a REAL failure here — it means the
 * nightly seed job didn't run or the demo tenant was lost.
 *
 * Local run: PW_SKIP_WEBSERVER=1 npx playwright test e2e/demo-smoke.spec.ts
 */

import { test, expect } from "@playwright/test";

const BACKEND_URL =
  process.env.TEST_BACKEND_URL || "https://agentnexlify-production.up.railway.app";
const APP_URL = process.env.TEST_APP_URL || "https://app.agentnexlify.com";

test.describe("live-demo sandbox smoke", () => {
  test("demo-login issues a session for the seeded demo tenant", async ({
    request,
  }) => {
    const resp = await request.post(`${BACKEND_URL}/api/v1/auth/demo-login`);
    const body = await resp.json().catch(() => ({}));

    expect(
      resp.status(),
      `demo-login returned ${resp.status()}: ${JSON.stringify(body)} — ` +
        "404 means the nightly seed job has not created the demo tenant",
    ).toBe(200);
    expect(body.token, "response missing JWT").toBeTruthy();
    expect(body.demo).toBe(true);
    expect(body.business_name || "").toContain("DEMO");
  });

  test("visitor lands in the demo dashboard with the banner", async ({
    page,
  }) => {
    await page.goto(`${APP_URL}/demo`, { waitUntil: "domcontentloaded" });

    // DemoLoginPage logs in and redirects to the dashboard.
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

    // The demo banner is the visitor's signpost — it must be visible.
    await expect(
      page.getByText(/You.re in the live demo/i),
    ).toBeVisible({ timeout: 15_000 });

    // And its conversion CTA must point at attributed signup.
    const cta = page.getByRole("link", { name: /start your free account/i });
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute("href", "/signup?from=demo");
  });
});
