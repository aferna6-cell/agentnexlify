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
 * Build the /complete payload from wizardData. Shared by the plan step,
 * the customize step (which now runs after plan), and the express path.
 */
export function buildWizardPayload(wizardData) {
  return {
    business_name: wizardData.business_name,
    business_type: wizardData.business_type || "other",
    city: wizardData.city || "",
    phone: wizardData.phone || null,
    website_url: wizardData.website_url || null,
    hours: wizardData.hours || null,
    services: wizardData.services?.length ? wizardData.services : null,
    widget_bot_name: wizardData.widget_bot_name || null,
    widget_primary_color: wizardData.widget_primary_color || null,
    widget_greeting_message: wizardData.widget_greeting_message || null,
    widget_position: wizardData.widget_position || null,
    faqs: wizardData.faqs?.length ? wizardData.faqs : null,
  };
}

/**
 * Email the widget embed snippet + install steps to whoever manages the
 * tenant's website (the wizard's "I can't edit my site" escape hatch).
 */
export function emailEmbedInstructions(tenantId, token, recipientEmail, note) {
  return apiFetch(`/api/v1/onboarding/${tenantId}/email-embed`, {
    token,
    body: { recipient_email: recipientEmail, note: note || null },
  });
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

/**
 * Instant KB - draft FAQ entries from a website URL without saving them.
 * Returns { faqs: [{question, answer, category}], chars_extracted, source_url }.
 * Throws Error(detail) on fetch / non-HTML / empty-page / AI failure.
 */
export function draftInstantKb(tenantId, token, url) {
  return apiFetch(`/api/v1/instant-kb/${tenantId}/draft`, {
    token,
    body: { url },
  });
}

/**
 * Instant KB - persist the owner-approved FAQ entries.
 * Returns { saved: number }.
 */
export function confirmInstantKb(tenantId, token, faqs) {
  return apiFetch(`/api/v1/instant-kb/${tenantId}/confirm`, {
    token,
    body: { faqs },
  });
}
