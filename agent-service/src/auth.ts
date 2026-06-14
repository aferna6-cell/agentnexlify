import { timingSafeEqual } from "node:crypto";

/**
 * Shared-secret auth for agent-service compute routes.
 *
 * When AGENT_SERVICE_TOKEN is configured, callers must present a matching
 * X-Agent-Token header. An empty expected token means open mode (local dev /
 * parity with the prior behavior). The /health route never calls this — its
 * check stays open so Railway's healthcheck keeps working.
 *
 * Comparison is constant-time (timingSafeEqual) so the endpoint is not a timing
 * oracle if it ever loses Railway private-networking isolation. (GH #206)
 */
export function isTokenAuthorized(
  provided: string | string[] | undefined,
  expected: string,
): boolean {
  if (!expected) return true;
  const value = Array.isArray(provided) ? provided[0] : provided;
  if (typeof value !== "string") return false;
  const bufProvided = Buffer.from(value);
  const bufExpected = Buffer.from(expected);
  // timingSafeEqual requires equal-length buffers; unequal length = reject.
  if (bufProvided.byteLength !== bufExpected.byteLength) return false;
  return timingSafeEqual(bufProvided, bufExpected);
}
