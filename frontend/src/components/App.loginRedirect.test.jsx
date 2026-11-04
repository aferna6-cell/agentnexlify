import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { tenantId: "ten-1", plan: "free", email: "a@b.c" },
    token: "tok",
  }),
}));

vi.mock("../utils/api/dashboard", () => ({
  fetchTrialStatus: vi.fn().mockResolvedValue(null),
}));

vi.mock("../utils/api/os", () => ({
  fetchOsPendingDeliverables: vi.fn().mockResolvedValue({ count: 0 }),
}));

vi.mock("./Sidebar", () => ({ default: () => null }));
vi.mock("./DemoBanner", () => ({ default: () => null }));
vi.mock("./NotificationBell", () => ({ default: () => null }));
vi.mock("./UpgradeGateBanner", () => ({ default: () => null }));
vi.mock("./MarketingUpsell", () => ({
  default: () => null,
  MARKETING_GATED_KEYS: new Set(),
  MARKETING_PLANS: new Set(["agent_os"]),
}));
vi.mock("../utils/planAccess", () => ({ hasAgentOsAccess: () => false }));

import App from "./App";

beforeEach(() => {
  window.history.pushState({}, "", "/login");
});

describe("App login history", () => {
  it("replaces /login with /dashboard when a session already exists", async () => {
    render(<App />);
    await waitFor(() => {
      expect(window.location.pathname).toBe("/dashboard");
    });
  });
});
