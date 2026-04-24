const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function apiFetch(path, { token, method = "POST", body } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Generate an AI knowledge base from onboarding answers.
 * Returns { knowledge_base: string|null, generated: boolean }
 */
export function generateKb(tenantId, token, data) {
  return apiFetch(`/api/v1/onboarding/${tenantId}/generate-kb`, { token, body: data });
}

/**
 * Complete onboarding - persists all wizard data to the backend.
 */
export function completeOnboarding(tenantId, token, data) {
  return apiFetch(`/api/v1/onboarding/${tenantId}/complete`, { token, body: data });
}

/**
 * Create a Stripe Checkout session from the wizard (source="wizard").
 * Returns { checkout_url: string }
 */
export function checkoutForWizard(token, plan) {
  return apiFetch(`/api/v1/auth/billing/checkout`, {
    token,
    body: { plan, source: "wizard" },
  });
}

/**
 * Log a wizard step event for drop-off tracking.
 * Fire-and-forget - never blocks the user's onboarding.
 */
export function trackWizardEvent(tenantId, token, step, action) {
  apiFetch(`/api/v1/wizard/${tenantId}/event`, {
    token,
    body: { step, action },
  }).catch((e) => { console.warn('Wizard event tracking failed:', e?.message); });
}

/**
 * Auto-generate knowledge base from a website URL.
 * Crawls the site, extracts content, and uses AI to generate KB + FAQs.
 * Returns { knowledge_base, custom_instructions, faqs, pages_crawled, chars_extracted }
 */
export function autoGenerateKb(tenantId, token, url) {
  return apiFetch(`/api/v1/onboarding/${tenantId}/auto-kb`, {
    token,
    body: { url },
  });
}
