import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:4173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Prod-targeting smoke jobs (widget-smoke, demo-smoke) set
  // PW_SKIP_WEBSERVER=1 — they hit live URLs and never install/build the
  // frontend, so booting the Vite preview there fails with "vite: not
  // found" (this broke every scheduled smoke run until 2026-06-12).
  webServer: process.env.PW_SKIP_WEBSERVER
    ? undefined
    : {
        command: "npm run preview --prefix frontend",
        url: "http://localhost:4173",
        reuseExistingServer: !process.env.CI,
        timeout: 30000,
      },
});
