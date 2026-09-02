import { chromium } from "@playwright/test";

const browser = await chromium.launch({
  headless: false,
  args: ["--start-maximized"],
});
const context = await browser.newContext({ viewport: null });
const page = await context.newPage();
await page.goto("http://localhost:3001/dashboard/integrations", {
  waitUntil: "domcontentloaded",
});
await page.bringToFront();
console.log("Integrations page open:", page.url());
await page.waitForTimeout(60 * 60 * 1000);
