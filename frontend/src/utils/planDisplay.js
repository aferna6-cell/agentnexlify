// Canonical customer-facing plan display names + colors.
//
// Internal plan KEYS stay `chatbot` / `agent_os` (they must match the backend
// PLAN_PRICES keys). These are the LABELS shown to users. Centralizing them
// here stops the Billing page, checkout, and admin analytics from drifting to
// "Chatbot" / "Agent OS" while marketing, signup, and the onboarding wizard say
// "AI Front Desk" / "AI Workforce" - a prospect who signs up for "AI Front Desk"
// and then sees "Chatbot" on their billing page reads it as a different product
// or a billing error (launch audit UI H2/H3, 2026-07-09).
export const PLAN_DISPLAY = {
  free: "Free",
  chatbot: "AI Front Desk",
  agent_os: "AI Workforce",
  // Legacy / grandfathered plans - still honored on old contracts.
  growth: "Growth",
  autopilot: "Autopilot",
  professional: "Professional",
  enterprise: "Enterprise",
};

// Brand-token colors keyed by plan (for charts/legends). Falls back gracefully.
export const PLAN_COLOR = {
  free: "var(--green)",
  chatbot: "var(--accent)",
  agent_os: "var(--purple, #8b5cf6)",
  growth: "var(--accent)",
  autopilot: "var(--yellow, #f59e0b)",
  professional: "var(--purple, #8b5cf6)",
  enterprise: "var(--red, #ff4444)",
};

export function planDisplayName(key) {
  return PLAN_DISPLAY[key] || key;
}
