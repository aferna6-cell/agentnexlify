/**
 * API client for /api/v1/integrations/keys — integration key vault (GH #132).
 *
 * Providers managed here: stripe, twilio, resend.
 * tenant_id comes from JWT on the backend; never passed in the request body.
 */
import { request } from "./_client";

const BASE_PATH = "/api/v1/integrations";

/**
 * List all configured providers for this tenant.
 * Returns: ProviderHealth[]  — { provider, health, detail, last_verified_at, masked_key }
 */
export function listKeys(token) {
  return request(`${BASE_PATH}/keys`, { token });
}

/**
 * Save (encrypt) a provider key and run an inline health check.
 * Returns: SaveKeyResult — { saved, verified, masked }
 *
 * @param {string} provider  — stripe | twilio | resend
 * @param {string} plaintext — raw key value
 * @param {object} metadata  — optional auxiliary fields
 */
export function saveKey(provider, plaintext, token, metadata = {}) {
  return request(`${BASE_PATH}/keys`, {
    method: "POST",
    token,
    body: { provider, plaintext, metadata },
  });
}

/**
 * Delete a stored provider key.
 * Returns: { deleted, provider }
 * Throws ApiError with status 409 when deleting Stripe while an active subscription exists.
 *
 * @param {string} provider — stripe | twilio | resend
 */
export function deleteKey(provider, token) {
  return request(`${BASE_PATH}/keys/${provider}`, {
    method: "DELETE",
    token,
  });
}

/**
 * Run a live health ping for a single provider (rate-limited: 10/min).
 * Returns: { health, detail }
 *
 * @param {string} provider — stripe | twilio | resend
 */
export function verifyKey(provider, token) {
  return request(`${BASE_PATH}/keys/${provider}/verify`, {
    method: "POST",
    token,
  });
}

/**
 * Aggregate health for all configured providers.
 * Returns: IntegrationsHealthResponse — { providers: ProviderHealth[], overall }
 */
export function fetchIntegrationHealth(token) {
  return request(`${BASE_PATH}/health`, { token });
}
