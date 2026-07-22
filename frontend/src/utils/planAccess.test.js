import { describe, it, expect } from "vitest";

import { AGENT_OS_PLANS, hasAgentOsAccess } from "./planAccess";

describe("planAccess", () => {
  it("mirrors the backend suite gate plan set", () => {
    expect([...AGENT_OS_PLANS].sort()).toEqual([
      "agent_os",
      "autopilot",
      "enterprise",
      "growth",
      "professional",
    ]);
  });

  it("grants suite access to agent_os and legacy plans", () => {
    for (const plan of AGENT_OS_PLANS) {
      expect(hasAgentOsAccess(plan)).toBe(true);
    }
  });

  it("denies chatbot and free", () => {
    expect(hasAgentOsAccess("chatbot")).toBe(false);
    expect(hasAgentOsAccess("free")).toBe(false);
  });

  it("stays optimistic while the plan is unknown", () => {
    expect(hasAgentOsAccess(null)).toBe(true);
    expect(hasAgentOsAccess(undefined)).toBe(true);
  });
});
