/**
 * Connector registry API - platform-wide list of integrations with their
 * connect path and connected state. Drives lightweight status strips
 * without hardcoding the integration list on the frontend.
 */
import { request } from "./_client";

export function fetchConnectorsStatus(token) {
  return request("/api/v1/connectors/status", { token });
}
