import { chromium } from "@playwright/test";

const browser = await chromium.launch({
  headless: false,
  args: ["--start-maximized"],
});
const context = await browser.newContext({ viewport: null });
const page = await context.newPage();
await page.goto("http://localhost:3001/login", { waitUntil: "domcontentloaded" });
await page.bringToFront();
console.log("Login page open:", page.url());
console.log("API base (from bundle): staging expected");
await page.waitForTimeout(60 * 60 * 1000);
