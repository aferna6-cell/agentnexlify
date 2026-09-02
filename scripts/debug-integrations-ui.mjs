import { chromium } from "@playwright/test";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

const network = [];
page.on("response", async (res) => {
  const url = res.url();
  if (url.includes("/integrations/google") || url.includes("/auth/login") || url.includes("/auth/me")) {
    let body = "";
    try {
      body = (await res.text()).slice(0, 500);
    } catch {}
    network.push({ url, status: res.status(), body });
  }
});

await page.goto("http://localhost:3001/login", { waitUntil: "domcontentloaded" });
await page.fill('input[type="email"]', "support@agentnexlify.com");
await page.fill('input[type="password"]', "Cristiano17");
await page.click('button[type="submit"]');
await page.waitForTimeout(3000);
await page.goto("http://localhost:3001/integrations", { waitUntil: "networkidle", timeout: 30000 }).catch(() => {});
await page.waitForTimeout(3000);

const text = (await page.locator("body").innerText()).slice(0, 6000);
await page.screenshot({ path: "/opt/cursor/artifacts/screenshots/m8-integrations-status-debug.png", fullPage: true });
console.log(JSON.stringify({ url: page.url(), textPreview: text, network }, null, 2));
await browser.close();
