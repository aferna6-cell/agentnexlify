/**
 * Widget render on slow 3G (launch rubric 5.4).
 *
 * Loads a bare host page that embeds the PRODUCTION widget script, with
 * Chrome DevTools network throttling set to a slow-3G profile (400ms RTT,
 * 400kbps down / 400kbps up), and measures time until the chat launcher is
 * visible. Gate: launcher visible < 10s on slow 3G, and the widget script
 * transfer stays under 100KB gzipped-equivalent (we check raw bytes < 100KB
 * since the asset is served uncompressed-size-known).
 *
 * Run: node ops/evals/run_widget_3g_check.mjs [--out ops/evals/widget-3g-YYYY-MM-DD.json]
 */

import { chromium } from "@playwright/test";

const WIDGET_URL =
  "https://agentnexlify-production.up.railway.app/widget/agentnexlify-widget.js";

const SLOW_3G = {
  offline: false,
  latency: 400, // ms RTT
  downloadThroughput: (400 * 1024) / 8, // 400 kbps
  uploadThroughput: (400 * 1024) / 8,
};

const HOST_PAGE = `<!doctype html>
<html><head><title>3G widget host</title></head>
<body>
  <h1>Plumber site</h1>
  <script src="${WIDGET_URL}" data-api-key="anx_3g_check_invalid"></script>
</body></html>`;

const outIdx = process.argv.indexOf("--out");
const outPath = outIdx > -1 ? process.argv[outIdx + 1] : null;

const browser = await chromium.launch();
const page = await browser.newPage({ ignoreHTTPSErrors: true });

let scriptBytes = 0;
page.on("response", async (resp) => {
  if (resp.url() === WIDGET_URL) {
    try {
      scriptBytes = (await resp.body()).length;
    } catch {
      /* body unavailable on failure — size check reports 0 */
    }
  }
});

const cdp = await page.context().newCDPSession(page);
await cdp.send("Network.enable");
await cdp.send("Network.emulateNetworkConditions", SLOW_3G);

const started = Date.now();
await page.setContent(HOST_PAGE, { waitUntil: "domcontentloaded" });

// The widget injects a launcher button; accept any of its known shapes.
const launcher = page
  .locator(
    "#anx-widget-button, .anx-widget-button, [id*='agentnexlify'] button, [class*='anx'] button",
  )
  .first();

let visibleMs = null;
let gatePass = false;
try {
  await launcher.waitFor({ state: "visible", timeout: 20000 });
  visibleMs = Date.now() - started;
  gatePass = visibleMs < 10000;
} catch {
  visibleMs = null;
}

await browser.close();

const result = {
  profile: "slow-3g (400ms RTT, 400kbps)",
  widget_url: WIDGET_URL,
  script_bytes: scriptBytes,
  script_under_100kb: scriptBytes > 0 && scriptBytes < 100 * 1024,
  launcher_visible_ms: visibleMs,
  gate_pass: gatePass && scriptBytes > 0 && scriptBytes < 100 * 1024,
};
console.log(JSON.stringify(result, null, 2));
if (outPath) {
  const { writeFileSync } = await import("node:fs");
  writeFileSync(outPath, JSON.stringify(result, null, 2));
}
console.log(`GATE: ${result.gate_pass ? "PASS" : "FAIL"} (visible<10s on slow 3G, script<100KB)`);
process.exit(result.gate_pass ? 0 : 1);
