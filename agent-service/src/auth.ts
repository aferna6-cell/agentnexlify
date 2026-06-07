/**
 * Shared-secret auth for agent-service compute routes.
 *
 * When AGENT_SERVICE_TOKEN is configured, callers must present a matching
 * X-Agent-Token header. An empty expected token means open mode (local dev /
 * parity with the prior behavior). The /health route never calls this — its
 * check stays open so Railway's healthcheck keeps working.
 */
export function isTokenAuthorized(
  provided: string | string[] | undefined,
  expected: string,
): boolean {
  if (!expected) return true;
  const value = Array.isArray(provided) ? provided[0] : provided;
  return value === expected;
}
