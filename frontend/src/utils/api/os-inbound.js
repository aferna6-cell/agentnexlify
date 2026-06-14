/**
 * Agent OS - Inbound bridge config API.
 *
 * Endpoints owned by backend/routers/os_inbound.py:
 *   GET  /api/v1/os/inbound/bridge-config  - any role
 *   POST /api/v1/os/inbound/bridge-toggle  - owner-only
 */

import { request } from "./_client";

export function fetchBridgeConfig(token) {
  return request("/api/v1/os/inbound/bridge-config", { token });
}

export function setBridgeToggle(source, enabled, token) {
  return request("/api/v1/os/inbound/bridge-toggle", {
    method: "POST",
    body: { source, enabled },
    token,
  });
}
