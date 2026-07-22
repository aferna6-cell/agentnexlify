import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockAuth = {
  token: "jwt",
  user: { tenantId: "t1", plan: "free" },
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("../utils/api/dashboard", () => ({
  fetchDashboard: vi.fn(),
  billingCheckout: vi.fn(),
  billingPortal: vi.fn(),
  fetchTrialStatus: vi.fn(),
  changePlan: vi.fn(),
  cancelSubscription: vi.fn(),
  fetchAiUsage: vi.fn(),
  buyMoreUsage: vi.fn(),
}));

vi.mock("../components/billing/ReferralCard", () => ({
  default: () => null,
}));

vi.mock("../utils/notify", () => ({
  notify: { success: vi.fn(), error: vi.fn() },
}));

import {
  billingCheckout,
  changePlan,
  fetchAiUsage,
  fetchDashboard,
  fetchTrialStatus,
} from "../utils/api/dashboard";
import { notify } from "../utils/notify";
import BillingPage from "./BillingPage";

beforeEach(() => {
  vi.clearAllMocks();
  fetchDashboard.mockResolvedValue({ plan: "free", plan_status: "active" });
  fetchTrialStatus.mockResolvedValue({
    plan: "free",
    days_remaining: 5,
    is_expired: false,
    trial_expires: "2026-07-27T00:00:00Z",
  });
  fetchAiUsage.mockResolvedValue(null);
  billingCheckout.mockResolvedValue({});
});

describe("BillingPage upgrade funnel", () => {
  it("offers BOTH plans in the trial banner, suite first", async () => {
    render(<BillingPage />);
    const suiteBtn = await screen.findByText(/Get AI Workforce/);
    expect(screen.getByText(/AI Front Desk \$19.99/)).toBeInTheDocument();
    fireEvent.click(suiteBtn);
    await waitFor(() =>
      expect(billingCheckout).toHaveBeenCalledWith("jwt", { plan: "agent_os" }),
    );
  });

  it("falls back to checkout when change-plan says no subscription", async () => {
    fetchDashboard.mockResolvedValue({ plan: "chatbot", plan_status: "active" });
    fetchTrialStatus.mockResolvedValue(null);
    changePlan.mockRejectedValue({
      body: { detail: "No active subscription found. Use checkout to subscribe." },
    });
    render(<BillingPage />);
    const switchBtn = await screen.findByText("Switch Plan");
    fireEvent.click(switchBtn);
    await waitFor(() =>
      expect(billingCheckout).toHaveBeenCalledWith("jwt", { plan: "agent_os" }),
    );
    expect(notify.error).not.toHaveBeenCalled();
    // The page recovers to its idle state - the switch button is back,
    // no stuck "Switching..." label.
    expect(screen.getByText("Switch Plan")).toBeInTheDocument();
    expect(screen.queryByText("Switching...")).not.toBeInTheDocument();
  });

  it("still surfaces genuine change-plan errors", async () => {
    fetchDashboard.mockResolvedValue({ plan: "chatbot", plan_status: "active" });
    fetchTrialStatus.mockResolvedValue(null);
    changePlan.mockRejectedValue({ body: { detail: "Card declined" } });
    render(<BillingPage />);
    fireEvent.click(await screen.findByText("Switch Plan"));
    await waitFor(() =>
      expect(notify.error).toHaveBeenCalledWith("Card declined"),
    );
    expect(billingCheckout).not.toHaveBeenCalled();
    // Still on the chatbot plan card - the failed switch changed nothing.
    expect(screen.getByText("Chatbot")).toBeInTheDocument();
    expect(screen.getByText("Switch Plan")).toBeInTheDocument();
  });
});
