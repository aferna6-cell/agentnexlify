import { chromium } from "@playwright/test";

const profile = "/tmp/playwright_chromiumdev_profile-2E5pQB";
const context = await chromium.launchPersistentContext(profile, {
  headless: true,
  args: ["--no-sandbox"],
});
const pages = context.pages();
const page = pages.length ? pages[pages.length - 1] : await context.newPage();
await page.waitForTimeout(500);
const url = page.url();
const title = await page.title();
const text = (await page.locator("body").innerText()).slice(0, 8000);
await page.screenshot({ path: "/opt/cursor/artifacts/screenshots/m8-calendar-callback-now.png", fullPage: true });
console.log(JSON.stringify({ url, title, textPreview: text }, null, 2));
await context.close();
