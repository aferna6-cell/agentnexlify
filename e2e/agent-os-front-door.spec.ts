/**
 * Front-door E2E: a logged-in owner lands on the Agent OS conversation.
 *
 * Phase 4 cutover made `/dashboard/agent-os` the default landing page
 * (frontend/src/components/App.jsx). This drives the REAL built bundle in
 * Chromium with the network stubbed at the edge: an unsigned-but-parseable
 * JWT in localStorage (AuthContext derives the user from the token payload)
 * and canned /api responses, so the test is hermetic — no backend needed.
 *
 * Run: npx playwright test e2e/agent-os-front-door.spec.ts
 * (webServer in playwright.config.ts serves the built frontend on :4173)
 */

import { test, expect, type Page } from "@playwright/test";

// APIs are fully stubbed, so TLS identity of the target host is irrelevant —
// lets the suite run against Vercel previews from behind corporate/CI proxies.
test.use({ ignoreHTTPSErrors: true });

function fakeJwt(): string {
  const b64 = (obj: object) =>
    Buffer.from(JSON.stringify(obj))
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const header = b64({ alg: "HS256", typ: "JWT" });
  const payload = b64({
    tenant_id: "e2e-tenant",
    email: "owner@e2e.test",
    plan: "growth",
    business_name: "E2E Auto Care",
    role: "owner",
    exp: Math.floor(Date.now() / 1000) + 3600,
  });
  return `${header}.${payload}.e2e-signature`;
}

async function stubApi(page: Page) {
  // Playwright matches the MOST RECENTLY registered route first — the
  // catch-all goes in before the specific shapes below.
  await page.route("**/api/**", (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/os/threads**", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/v1/os/deliverables/pending**", (route) =>
    route.fulfill({ json: { count: 0, items: [] } }),
  );
  await page.route("**/api/v1/os/memory**", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/v1/os/backlog**", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/v1/os/usage**", (route) =>
    route.fulfill({
      json: { agent_runs: 0, messages: 0, cap: 200, cap_reached: false },
    }),
  );
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ json: { plan: "growth", marketing_addon_active: false } }),
  );
}

test("unauthenticated visitor sees the login page", async ({ page }) => {
  await stubApi(page);
  await page.goto("/dashboard");
  await expect(
    page.getByRole("button", { name: /sign in|log in/i }).or(
      page.locator("input[type='password']"),
    ).first(),
  ).toBeVisible({ timeout: 10000 });
});

test("logged-in owner lands on the Agent OS conversation", async ({ page }) => {
  await stubApi(page);
  await page.addInitScript((token: string) => {
    window.localStorage.setItem("anx_token", token);
    window.localStorage.setItem("anx_tenant_id", "e2e-tenant");
  }, fakeJwt());

  await page.goto("/dashboard");

  // The Agent OS shell's empty state — proof the conversational surface is
  // the landing page, not the classic dashboard.
  await expect(
    page.getByText("No tasks yet. Start one to hand work to the orchestrator."),
  ).toBeVisible({ timeout: 15000 });
});

test("deep links to classic pages still work", async ({ page }) => {
  await stubApi(page);
  await page.addInitScript((token: string) => {
    window.localStorage.setItem("anx_token", token);
    window.localStorage.setItem("anx_tenant_id", "e2e-tenant");
  }, fakeJwt());

  await page.goto("/dashboard/leads");
  await expect(
    page.getByText("No tasks yet. Start one to hand work to the orchestrator."),
  ).toBeHidden();
});
