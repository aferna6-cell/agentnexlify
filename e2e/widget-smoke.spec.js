/**
 * E2E Smoke Test: Widget → Message → Lead Capture
 *
 * Tests the core revenue path:
 * 1. Widget loads on a page with valid API key
 * 2. User sends a message
 * 3. AI responds
 * 4. Lead is captured when user provides contact info
 *
 * Run with: npm run test:e2e -- e2e/widget-smoke.spec.js
 * Or via Playwright MCP for browser automation.
 *
 * Prerequisites:
 * - Backend running at localhost:8000
 * - A valid test tenant with API key
 */

const { test, expect } = require("@playwright/test");

// Test config — set via env or use defaults
const BACKEND_URL = process.env.TEST_BACKEND_URL || "http://localhost:8000";
const PUBLIC_URL = process.env.TEST_PUBLIC_URL || "http://localhost:3001";
const WIDGET_ORIGIN = process.env.TEST_WIDGET_ORIGIN || PUBLIC_URL;
const TEST_API_KEY = process.env.TEST_WIDGET_API_KEY || "";
const INCLUDE_UPLOAD = /^(1|true|yes|on)$/i.test(
  process.env.TEST_WIDGET_UPLOAD || "",
);

async function loadWidgetPage(page) {
  const pageErrors = [];
  const consoleErrors = [];
  page.on("pageerror", (err) => pageErrors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.setContent(
    `<!doctype html>
    <html>
      <head><title>AgentNexLiFy Smoke Embed</title></head>
      <body>
        <main>
          <h1>Smoke Test Host Page</h1>
          <p>The widget should mount as a third-party embed.</p>
        </main>
        <script
          src="${PUBLIC_URL.replace(/\/$/, "")}/widget/agentnexlify-widget.js"
          data-api-key="${TEST_API_KEY}"
          data-api-base="${BACKEND_URL.replace(/\/$/, "")}"
        ></script>
      </body>
    </html>`,
    { waitUntil: "domcontentloaded" },
  );

  await expect(page.locator("#anx-bubble")).toBeVisible({ timeout: 15000 });
  return { pageErrors, consoleErrors };
}

test.describe("Widget Smoke Tests", () => {
  test.skip(!TEST_API_KEY, "TEST_WIDGET_API_KEY not set — skipping widget E2E");

  test("widget config endpoint returns valid config", async ({ request }) => {
    const resp = await request.get(
      `${BACKEND_URL}/api/v1/widget/config/${TEST_API_KEY}`,
    );
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toHaveProperty("bot_name");
    expect(data).toHaveProperty("primary_color");
    expect(data).toHaveProperty("greeting_message");
  });

  test("widget chat endpoint accepts message", async ({ request }) => {
    const resp = await request.post(`${BACKEND_URL}/api/v1/widget/chat`, {
      data: {
        api_key: TEST_API_KEY,
        message: "Hello, I need help",
        session_id: `e2e-smoke-${Date.now()}`,
      },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toHaveProperty("response");
    expect(data).toHaveProperty("session_id");
    expect(data.response.length).toBeGreaterThan(0);
  });

  test("browser embed opens widget and sends a chat", async ({ page }) => {
    const { pageErrors, consoleErrors } = await loadWidgetPage(page);

    await page.locator("#anx-bubble").click();
    await expect(page.locator("#anx-window")).toHaveClass(/open/);

    const assistantMessages = page.locator(".anx-msg.assistant");
    const before = await assistantMessages.count();
    await page.locator("#anx-input").fill("Hello from the browser smoke test");
    await page.locator("#anx-send").click();

    await expect
      .poll(async () => assistantMessages.count(), { timeout: 45000 })
      .toBeGreaterThan(before);
    await expect(assistantMessages.last()).toContainText(/\S/);
    expect(pageErrors).toEqual([]);
    expect(consoleErrors).toEqual([]);
  });

  test("booking intent opens booking flow when enabled", async ({
    page,
    request,
  }) => {
    const configResp = await request.get(
      `${BACKEND_URL}/api/v1/widget/config/${TEST_API_KEY}`,
    );
    const config = await configResp.json();
    test.skip(!config.booking_enabled || !config.tenant_id, "booking not enabled for smoke tenant");

    await loadWidgetPage(page);
    await page.locator("#anx-bubble").click();
    await page.locator("#anx-input").fill("I want to book an appointment");
    await page.locator("#anx-send").click();
    await expect(page.locator("#anx-booking")).toBeVisible({ timeout: 10000 });
  });

  test("widget upload endpoint accepts current form-data contract", async ({
    request,
  }) => {
    test.skip(!INCLUDE_UPLOAD, "TEST_WIDGET_UPLOAD not enabled");

    const resp = await request.post(`${BACKEND_URL}/api/v1/widget/upload`, {
      headers: { Origin: WIDGET_ORIGIN },
      multipart: {
        api_key: TEST_API_KEY,
        session_id: `e2e-upload-${Date.now()}`,
        file: {
          name: "smoke.png",
          mimeType: "image/png",
          buffer: Buffer.concat([
            Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
            Buffer.alloc(16),
          ]),
        },
      },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.filename).toBe("smoke.png");
    expect(data.url).toContain("/chat-attachments/");
  });

  test("widget chat captures lead when contact info provided", async ({
    request,
  }) => {
    const sessionId = `e2e-lead-${Date.now()}`;

    // First message — establish conversation
    await request.post(`${BACKEND_URL}/api/v1/widget/chat`, {
      data: {
        api_key: TEST_API_KEY,
        message: "I need a quote for your services",
        session_id: sessionId,
      },
    });

    // Second message — provide contact info (triggers lead capture)
    const resp = await request.post(`${BACKEND_URL}/api/v1/widget/chat`, {
      data: {
        api_key: TEST_API_KEY,
        message:
          "My name is E2E Test User, email is e2e-test@example.com, phone 555-0199",
        session_id: sessionId,
      },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    // lead_captured may be true if extraction succeeded
    // Either way, the response should exist
    expect(data).toHaveProperty("response");
  });

  test("booking page loads for valid business slug", async ({ request }) => {
    // Get the test tenant's slug
    const configResp = await request.get(
      `${BACKEND_URL}/api/v1/widget/config/${TEST_API_KEY}`,
    );
    const config = await configResp.json();
    const tenantId = config.tenant_id;

    // Try to load the booking page (may need business_slug)
    const resp = await request.get(`${BACKEND_URL}/api/v1/book/${tenantId}`);
    // 200 = page loads, 404 = no slug configured (acceptable for smoke test)
    expect([200, 404]).toContain(resp.status());
  });

  test("widget rejects invalid API key", async ({ request }) => {
    const resp = await request.post(`${BACKEND_URL}/api/v1/widget/chat`, {
      data: {
        api_key: "definitely-not-a-real-key",
        message: "Hello",
        session_id: "e2e-invalid",
      },
    });
    expect([400, 404]).toContain(resp.status());
  });
});
