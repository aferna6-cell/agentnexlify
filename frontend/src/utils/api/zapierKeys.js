/**
 * Zapier CRM-export API key management (#60).
 *
 * Wraps the tenant-facing key endpoints in backend/routers/zapier.py:
 *   POST   /api/zapier/keys           generate (raw key returned ONCE)
 *   GET    /api/zapier/keys           list (non-plaintext)
 *   DELETE /api/zapier/keys/{key_id}  revoke (soft-delete)
 *
 * The raw key is never stored client-side and never re-fetchable after
 * generation (CLAUDE.md Rule 6: no localStorage; single-view key).
 */
import { request } from "./_client";

/**
 * List the tenant's Zapier API keys.
 * Returns array of { id, client_id, name, key_prefix, last_used_at,
 * created_at, revoked_at }. Revoked keys carry a non-null revoked_at.
 */
export function listZapierKeys(token) {
  return request("/api/zapier/keys", { token });
}

/**
 * Generate a new Zapier API key. `raw_key` in the response is shown ONCE.
 * Returns { id, client_id, name, raw_key, key_prefix, created_at }.
 * Throws ApiError 402 when the tenant plan does not include Zapier.
 */
export function generateZapierKey(name, token) {
  return request("/api/zapier/keys", {
    method: "POST",
    token,
    body: { name },
  });
}

/**
 * Revoke (soft-delete) a key by id. Resolves on 204; idempotent.
 */
export function revokeZapierKey(keyId, token) {
  return request(`/api/zapier/keys/${keyId}`, {
    method: "DELETE",
    token,
  });
}
