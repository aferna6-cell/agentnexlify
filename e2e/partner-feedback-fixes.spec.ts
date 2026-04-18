import { test, expect } from "@playwright/test";

// Smoke tests for partner feedback UI fixes (2026-04-18)
// Verifies: (1) ToS gold banner removed, (2) Book a Demo button visible,
// (3) core public pages load without errors.

test.describe("Terms of Service page", () => {
  test("gold disclaimer banner is removed", async ({ page }) => {
    await page.goto("/terms");
    await page.waitForLoadState("networkidle");

    // Banner must not exist
    const banner = page.locator(".legal-disclaimer");
    await expect(banner).toHaveCount(0);

    // Page still has the title and first section
    await expect(page.locator("h1")).toContainText("Terms of Service");
    await expect(page.locator("h2").first()).toBeVisible();
  });
});

test.describe("Contact page — Book a Demo button", () => {
  test("button is visible with readable label", async ({ page }) => {
    await page.goto("/contact");
    await page.waitForLoadState("networkidle");

    const btn = page
      .locator("a.contact-submit")
      .filter({ hasText: "Book a Demo" });
    await expect(btn).toBeVisible();
    await expect(btn).toHaveText("Book a Demo");

    // Verify button has non-transparent colour (not blank)
    const color = await btn.evaluate((el) => getComputedStyle(el).color);
    // color should be white (rgb(255, 255, 255)) — not transparent / same as bg
    expect(color).toBe("rgb(255, 255, 255)");
  });

  test("contact form submit button is labelled", async ({ page }) => {
    await page.goto("/contact");
    await page.waitForLoadState("networkidle");

    const submitBtn = page.locator("button.contact-submit");
    await expect(submitBtn).toBeVisible();
    await expect(submitBtn).toContainText("Send Message");
  });
});

test.describe("Core public pages load", () => {
  const publicRoutes = ["/", "/terms", "/privacy", "/contact"];

  for (const route of publicRoutes) {
    test(`${route} loads without JS errors`, async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (err) => errors.push(err.message));

      await page.goto(route);
      await page.waitForLoadState("networkidle");

      expect(errors).toHaveLength(0);
      // Page must have some visible content
      await expect(page.locator("body")).not.toBeEmpty();
    });
  }
});
