/**
 * Frontend mirror of backend agent_os_gate.AGENT_OS_PLANS - the plans with
 * AI Workforce (suite) access: agent_os plus legacy/grandfathered contracts.
 * Used to skip background suite polls for tenants the backend would 402,
 * so the upgrade banner only appears when the owner actually taps a gated
 * surface. Backend enforcement is the source of truth.
 */
export const AGENT_OS_PLANS = new Set([
  "agent_os",
  "growth",
  "autopilot",
  "professional",
  "enterprise",
]);

export function hasAgentOsAccess(plan) {
  // Unknown plan (still loading) stays optimistic - the backend enforces.
  if (!plan) return true;
  return AGENT_OS_PLANS.has(plan);
}
