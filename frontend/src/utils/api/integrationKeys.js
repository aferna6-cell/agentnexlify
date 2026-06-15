/**
 * Integration keys API functions (Stripe, Twilio, Resend).
 * Manages encrypted provider keys for the current tenant.
 */
import { request } from "./_client";

// Allowed providers
export const INTEGRATION_KEY_PROVIDERS = ["stripe", "twilio", "resend"];

/**
 * Save (create or replace) a provider key.
 * Returns { saved, verified, masked }
 */
export function saveIntegrationKey(provider, plaintext, metadata, token) {
  return request("/api/v1/integrations/keys", {
    method: "POST",
    token,
    body: { provider, plaintext, metadata },
  });
}

/**
 * List all stored integration keys for the tenant.
 * Returns array of { provider, health, detail, last_verified_at, masked_key }
 */
export function listIntegrationKeys(token) {
  return request("/api/v1/integrations/keys", { token });
}

/**
 * Delete a provider key.
 * Returns { deleted, provider }
 * Throws ApiError with status 409 when provider=stripe and tenant has active subscription.
 */
export function deleteIntegrationKey(provider, token) {
  return request(`/api/v1/integrations/keys/${provider}`, {
    method: "DELETE",
    token,
  });
}

/**
 * Verify a provider key and return updated health.
 * Returns { health, detail }
 */
export function verifyIntegrationKey(provider, token) {
  return request(`/api/v1/integrations/keys/${provider}/verify`, {
    method: "POST",
    token,
  });
}

/**
 * Fetch overall integrations health.
 * Returns { providers: [...], overall }
 */
export function fetchIntegrationsHealth(token) {
  return request("/api/v1/integrations/health", { token });
}
