import { describe, it, expect } from "vitest";
import { actionableIntegrationAlerts } from "./IntegrationHealthBanner";

describe("actionableIntegrationAlerts", () => {
  it("returns empty for null / malformed health", () => {
    expect(actionableIntegrationAlerts(null)).toEqual([]);
    expect(actionableIntegrationAlerts({})).toEqual([]);
    expect(actionableIntegrationAlerts({ providers: "nope" })).toEqual([]);
  });

  it("ignores healthy (green) providers", () => {
    const health = {
      providers: [{ provider: "stripe", health: "green", detail: "OK" }],
    };
    expect(actionableIntegrationAlerts(health)).toEqual([]);
  });

  it("ignores never-configured providers (not an alert)", () => {
    const health = {
      providers: [
        { provider: "stripe", health: "red", detail: "not configured" },
        { provider: "twilio", health: "red", detail: "not configured" },
      ],
    };
    expect(actionableIntegrationAlerts(health)).toEqual([]);
  });

  it("surfaces a configured connection that lapsed (red)", () => {
    const health = {
      providers: [
        { provider: "google_calendar", health: "green", detail: "connected" },
        { provider: "stripe", health: "red", detail: "authentication failed" },
      ],
    };
    const out = actionableIntegrationAlerts(health);
    expect(out).toHaveLength(1);
    expect(out[0].provider).toBe("stripe");
  });

  it("surfaces degraded (yellow) configured connections", () => {
    const health = {
      providers: [
        { provider: "resend", health: "yellow", detail: "unexpected status 500" },
      ],
    };
    expect(actionableIntegrationAlerts(health)).toHaveLength(1);
  });

  it("returns multiple lapsed providers together", () => {
    const health = {
      providers: [
        { provider: "stripe", health: "red", detail: "request timed out" },
        { provider: "twilio", health: "red", detail: "authentication failed" },
        { provider: "resend", health: "red", detail: "not configured" },
        { provider: "google_calendar", health: "green", detail: "connected" },
      ],
    };
    const out = actionableIntegrationAlerts(health);
    expect(out.map((p) => p.provider)).toEqual(["stripe", "twilio"]);
  });
});
