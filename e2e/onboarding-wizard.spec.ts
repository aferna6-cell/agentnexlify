/**
 * Onboarding wizard E2E: a new owner completes all 7 wizard steps without
 * manual intervention (launch-rubric 7.3).
 *
 * Modeled on e2e/agent-os-front-door.spec.ts: real built bundle in Chromium,
 * unsigned-but-parseable JWT in localStorage (AuthContext derives the user
 * from the token payload), and /api fully stubbed at the edge — hermetic, no
 * backend needed.
 *
 * Wizard steps (frontend/src/pages/OnboardingWizardPage.jsx) and their API calls:
 *   1. Business   — pure form (name + city required), no API
 *   2. Auto-KB    — optional POST /api/v1/onboarding/{t}/auto-kb (skippable)
 *   3. Services   — pure form, no API
 *   4. Knowledge  — auto POST /api/v1/onboarding/{t}/generate-kb on mount
 *   5. Customize  — GET /api/v1/auth/dashboard/{t} (widget_api_key, non-fatal)
 *   6. Plan       — POST /api/v1/onboarding/{t}/complete, then for FREE plan
 *                   advances in-app; paid plans redirect to Stripe Checkout
 *   7. Embed      — GET /api/v1/auth/dashboard/{t} for the embed snippet
 * Every step also fires POST /api/v1/wizard/{t}/event (fire-and-forget).
 *
 * The walkthrough takes the FREE plan at step 6 — the paid path is a hard
 * third-party redirect to Stripe Checkout (window.location.href =
 * checkout_url) that cannot be driven hermetically. The Stripe RETURN leg is
 * covered instead: /onboarding?step=6 (the cancel URL Stripe sends users back
 * to — backend/routers/auth.py:1256) must land on the Plan step.
 *
 * Route choice: the spec drives /onboarding, the canonical authenticated
 * entry (and the Stripe return target). /onboarding wraps the wizard in
 * OnboardingRoute (main.jsx), which holds rendering while `token` exists but
 * `user` is still null. The bare /setup route mounts OnboardingWizardPage
 * directly and LOSES that race on a cold load: the wizard's own child effect
 * (`if (user === null) navigate("/signup")`) runs before AuthProvider's
 * parent effect resolves the user, so a logged-in owner who refreshes /setup
 * is bounced to /signup. Known gap in OnboardingWizardPage.jsx (owned by
 * another workstream at time of writing) — asserted up to here per the
 * "document what can't be driven" rule; /setup is intentionally not used for
 * the authenticated walkthrough.
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
  // Steps 5 and 7 fetch the dashboard for the widget API key (embed snippet).
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

test("new owner completes the full wizard on the free plan with no dead-ends", async ({
  page,
}) => {
  await stubApi(page);
  await loginAs(page);

  await page.goto("/onboarding");

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

  // Step 5 — Widget customization (presets pre-filled; defaults are valid).
  await expect(page.getByText("Step 5 of 7")).toBeVisible();
  await expect(page.getByText("Customize your widget")).toBeVisible();
  await page.getByRole("button", { name: "Continue →" }).click();

  // Step 6 — Plan choice. FREE persists the wizard data (POST .../complete,
  // stubbed) and advances in-app; paid plans hard-redirect to Stripe.
  await expect(page.getByText("Step 6 of 7")).toBeVisible();
  await expect(page.getByText("Choose your plan")).toBeVisible();
  await page.getByRole("button", { name: "Continue Free" }).click();

  // Step 7 — Completion: embed snippet with the live widget key + handoff
  // into the Agent OS. No step dead-ended.
  await expect(page.getByText("Step 7 of 7")).toBeVisible();
  await expect(page.getByText("Your AI assistant is live!")).toBeVisible({
    timeout: 10000,
  });
  await expect(page.getByText(WIDGET_API_KEY)).toBeVisible();
  await expect(
    page.getByRole("link", { name: /meet your ai staff/i }),
  ).toBeVisible();
});

test("Stripe checkout return deep-links straight to the Plan step", async ({
  page,
}) => {
  // After a paid-plan redirect, Stripe sends the owner back with ?step=6 —
  // the wizard must resume there, not restart at step 1.
  await stubApi(page);
  await loginAs(page);

  await page.goto("/onboarding?step=6");
  await expect(page.getByText("Step 6 of 7")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("Choose your plan")).toBeVisible();
});

test("unauthenticated visitor on /onboarding is sent to signup", async ({
  page,
}) => {
  await stubApi(page);
  await page.goto("/onboarding");
  await expect(page).toHaveURL(/\/signup/, { timeout: 15000 });
});
