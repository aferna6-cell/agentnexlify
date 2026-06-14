// @ts-check
/**
 * Playwright config for the critical-journey suite.
 *
 * Targets the live demo sandbox (E2E_BASE_URL env).
 * No webServer spin-up — these tests run against the deployed app.
 *
 * Usage:
 *   npm run e2e                                          # default prod
 *   E2E_BASE_URL=https://preview.app.… npm run e2e      # preview deploy
 *   npx playwright test --config e2e/playwright.config.js --list
 */

const { defineConfig, devices } = require("@playwright/test");

const BASE_URL =
  process.env.E2E_BASE_URL || "https://app.agentnexlify.com";

module.exports = defineConfig({
  testDir: "./journeys",
  fullyParallel: false,           // journeys are sequential (share no state, but keep workers low for prod)
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,                     // serial against prod — no hammering the demo sandbox
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report-journeys", open: "never" }],
    ["junit", { outputFile: "test-results-journeys/results.xml" }],
  ],
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // Demo login does a real API call — give it room to breathe.
    actionTimeout: 20_000,
    navigationTimeout: 30_000,
    // Required in restricted CI environments where the prod TLS cert chain
    // is not trusted by the bundled Chromium root store.
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: "chromium-journeys",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // No webServer — tests hit live URLs.
});
