/**
 * Onboarding E2E: express setup + the full 7-step wizard (launch-rubric 7.3).
 *
 * Modeled on e2e/agent-os-front-door.spec.ts: real built bundle in Chromium,
 * unsigned-but-parseable JWT in localStorage (AuthContext derives the user
 * from the token payload), and /api fully stubbed at the edge — hermetic, no
 * backend needed.
 *
 * Flow (frontend/src/pages/OnboardingWizardPage.jsx, reordered 2026-06-11 —
 * Agent OS is the product, the widget steps are the optional tail):
 *   0. Express    — chooser: "Set up automatically" (auto-kb + complete →
 *                   /dashboard/agent-os) or "Customize step by step" (step 1)
 *   1. Business   — pure form (name + city required), no API
 *   2. Auto-KB    — optional POST /api/v1/onboarding/{t}/auto-kb (skippable)
 *   3. Services   — pure form, no API
 *   4. Knowledge  — auto POST /api/v1/onboarding/{t}/generate-kb on mount
 *   5. Plan       — POST /api/v1/onboarding/{t}/complete, then for FREE plan
 *                   advances in-app; paid plans redirect to Stripe Checkout
 *   6. Customize  — optional widget styling; persists via .../complete
 *   7. Embed      — optional widget install + email-to-web-person escape hatch
 * Every step 1-7 fires POST /api/v1/wizard/{t}/event (fire-and-forget).
 *
 * The walkthrough takes the FREE plan at step 5 — the paid path is a hard
 * third-party redirect to Stripe Checkout that cannot be driven hermetically.
 * The Stripe RETURN legs are covered instead (backend/routers/auth.py):
 * success → /onboarding?step=6 (resume after Plan), cancel → ?step=5 (Plan).
 *
 * Route choice: the spec drives /onboarding, the canonical authenticated
 * entry (and the Stripe return target). Both /onboarding AND /setup wrap the
 * wizard in OnboardingRoute (main.jsx) — see the "/setup cold load" test.
 *
 * Run: npx playwright test e2e/onboarding-wizard.spec.ts
 * (webServer in playwright.config.ts serves the built frontend on :4173)
 */

import { test, expect, type Page } from "@playwright/test";

// APIs are fully stubbed, so TLS identity of the target host is irrelevant —
// lets the suite run against Vercel previews from behind corporate/CI proxies.
test.use({ ignoreHTTPSErrors: true });

const WIDGET_API_KEY = "anx_e2e_widget_key_123";

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
    plan: "free",
    business_name: "E2E Auto Care",
    role: "owner",
    exp: Math.floor(Date.now() / 1000) + 3600,
  });
  return `${header}.${payload}.e2e-signature`;
}

async function stubApi(page: Page) {
  // Playwright matches the MOST RECENTLY registered route first — the
  // catch-all goes in before the specific shapes below. The catch-all
  // already satisfies /wizard/{t}/event (tracking), /onboarding/{t}/complete
  // (only res.ok is checked), and any other incidental calls.
  await page.route("**/api/**", (route) => route.fulfill({ json: {} }));
  // Step 4 auto-generates the knowledge base on mount and requires
  // { generated: true, knowledge_base } to leave the loading state.
  await page.route("**/api/v1/onboarding/*/generate-kb", (route) =>
    route.fulfill({
      json: {
        generated: true,
        knowledge_base:
          "# E2E Auto Care\nServices: Oil Change, Brake Service.\nHours: Mon-Fri 9-5.",
      },
    }),
  );
  // Steps 6 and 7 fetch the dashboard for the widget API key (embed snippet).
  await page.route("**/api/v1/auth/dashboard/**", (route) =>
    route.fulfill({ json: { widget_api_key: WIDGET_API_KEY } }),
  );
}

async function loginAs(page: Page) {
  await page.addInitScript((token: string) => {
    window.localStorage.setItem("anx_token", token);
    window.localStorage.setItem("anx_tenant_id", "e2e-tenant");
  }, fakeJwt());
}

test("fresh owner lands on the express chooser with all three doors", async ({
  page,
}) => {
  await stubApi(page);
  await loginAs(page);

  await page.goto("/onboarding");
  await expect(page.getByText("Meet your AI staff")).toBeVisible({
    timeout: 15000,
  });
  await expect(
    page.getByRole("button", { name: /set up automatically/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /customize step by step/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /skip for now/i }),
  ).toBeVisible();
});

test("express setup runs auto-kb + complete and lands in the Agent OS", async ({
  page,
}) => {
  await stubApi(page);
  await loginAs(page);

  await page.goto("/onboarding");
  await page
    .getByPlaceholder("yourbusiness.com")
    .fill("e2e-auto-care.example.com");
  const completeCall = page.waitForRequest((req) =>
    req.url().includes("/api/v1/onboarding/") && req.url().endsWith("/complete"),
  );
  await page.getByRole("button", { name: /set up automatically/i }).click();
  await completeCall;
  await expect(page).toHaveURL(/\/dashboard\/agent-os/, { timeout: 15000 });
});

test("new owner completes the full wizard on the free plan with no dead-ends", async ({
  page,
}) => {
  await stubApi(page);
  await loginAs(page);

  await page.goto("/onboarding");

  // Step 0 — express chooser; take the step-by-step door.
  await page
    .getByRole("button", { name: /customize step by step/i })
    .click();

  // Step 1 — Business info.
  await expect(page.getByText("Step 1 of 7")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("Tell us about your business")).toBeVisible();
  await page
    .getByPlaceholder("Acme Plumbing & Heating")
    .fill("E2E Auto Care");
  await page.getByPlaceholder("Austin, TX").fill("Columbia, SC");
  await page.getByRole("button", { name: "Continue →" }).click();

  // Step 2 — Auto-KB from website (optional; skip the crawl).
  await expect(page.getByText("Step 2 of 7")).toBeVisible();
  await expect(page.getByText("Auto-fill from your website")).toBeVisible();
  await page.getByRole("button", { name: /skip/i }).click();

  // Step 3 — Services & FAQs (all optional).
  await expect(page.getByText("Step 3 of 7")).toBeVisible();
  await expect(page.getByText("Services & FAQs")).toBeVisible();
  await page.getByRole("button", { name: "Continue →" }).click();

  // Step 4 — Knowledge base auto-generates on mount (stubbed response).
  await expect(page.getByText("Step 4 of 7")).toBeVisible();
  await expect(page.getByText(/knowledge base ready/i)).toBeVisible({
    timeout: 10000,
  });
  await page.getByRole("button", { name: "Continue →" }).click();

  // Step 5 — Plan choice. FREE persists the wizard data (POST .../complete,
  // stubbed) and advances in-app; paid plans hard-redirect to Stripe.
  await expect(page.getByText("Step 5 of 7")).toBeVisible();
  await expect(page.getByText("Choose your plan")).toBeVisible();
  await page.getByRole("button", { name: "Continue Free" }).click();

  // Step 6 — OPTIONAL widget customization (presets pre-filled).
  await expect(page.getByText("Step 6 of 7")).toBeVisible();
  await expect(
    page.getByText("Optional: customize your website chat"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Continue →" }).click();

  // Step 7 — Completion: Agent OS handoff first, optional embed snippet with
  // the live widget key + the email-to-web-person escape hatch.
  await expect(page.getByText("Step 7 of 7")).toBeVisible();
  await expect(page.getByText("Your AI staff is on the clock")).toBeVisible({
    timeout: 10000,
  });
  await expect(page.getByText(WIDGET_API_KEY)).toBeVisible();
  await expect(
    page.getByRole("link", { name: /meet your ai staff/i }),
  ).toBeVisible();
  await expect(
    page.getByPlaceholder("your web person's email"),
  ).toBeVisible();
});

test("Stripe cancel return deep-links straight to the Plan step", async ({
  page,
}) => {
  // After a paid-plan redirect, Stripe's cancel URL sends the owner back
  // with ?step=5 (backend/routers/auth.py) — the wizard must resume on the
  // Plan step, not restart at the chooser.
  await stubApi(page);
  await loginAs(page);

  await page.goto("/onboarding?step=5");
  await expect(page.getByText("Step 5 of 7")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("Choose your plan")).toBeVisible();
});

test("Stripe success return resumes after the Plan step", async ({ page }) => {
  await stubApi(page);
  await loginAs(page);

  await page.goto("/onboarding?step=6");
  await expect(page.getByText("Step 6 of 7")).toBeVisible({ timeout: 15000 });
  await expect(
    page.getByText("Optional: customize your website chat"),
  ).toBeVisible();
});

test("unauthenticated visitor on /onboarding is sent to signup", async ({
  page,
}) => {
  await stubApi(page);
  await page.goto("/onboarding");
  await expect(page).toHaveURL(/\/signup/, { timeout: 15000 });
});

test("logged-in owner cold-loading /setup lands on the wizard, not /signup", async ({
  page,
}) => {
  await stubApi(page);
  await loginAs(page);
  await page.goto("/setup");
  // The race fix: AuthProvider needs a tick to parse the token; the route
  // must hold (render nothing) instead of bouncing to /signup.
  await expect(page.getByText(/business/i).first()).toBeVisible();
  expect(new URL(page.url()).pathname).toBe("/setup");
});
