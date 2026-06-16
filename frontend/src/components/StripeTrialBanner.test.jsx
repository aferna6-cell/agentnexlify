import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, vi, expect } from "vitest";

import StripeTrialBanner from "./StripeTrialBanner";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../context/AuthContext";

describe("StripeTrialBanner", () => {
  it("renders when planStatus is trialing", () => {
    useAuth.mockReturnValue({
      user: { planStatus: "trialing", plan: "chatbot" },
    });
    render(<StripeTrialBanner onNavigate={vi.fn()} />);
    expect(screen.getByTestId("stripe-trial-banner")).toBeInTheDocument();
    expect(
      screen.getByText(/you're on a 7-day free trial/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/your card will be charged automatically/i),
    ).toBeInTheDocument();
  });

  it("renders Manage billing button when trialing", () => {
    useAuth.mockReturnValue({
      user: { planStatus: "trialing", plan: "agent_os" },
    });
    render(<StripeTrialBanner onNavigate={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /manage billing/i }),
    ).toBeInTheDocument();
  });

  it("navigates to billing when the button is clicked", () => {
    // Capture into a real variable (not a mock) so the assertion is against
    // observable behavior (the navigation target), not a mock interaction.
    let navigatedTo = null;
    useAuth.mockReturnValue({
      user: { planStatus: "trialing", plan: "chatbot" },
    });
    render(
      <StripeTrialBanner
        onNavigate={(key) => {
          navigatedTo = key;
        }}
      />,
    );
    expect(navigatedTo).toBeNull(); // no navigation before interaction
    fireEvent.click(screen.getByRole("button", { name: /manage billing/i }));
    expect(navigatedTo).toBe("billing");
  });

  it("does not render when planStatus is active", () => {
    useAuth.mockReturnValue({
      user: { planStatus: "active", plan: "chatbot" },
    });
    render(<StripeTrialBanner onNavigate={vi.fn()} />);
    expect(
      screen.queryByTestId("stripe-trial-banner"),
    ).not.toBeInTheDocument();
  });

  it("does not render when planStatus is free", () => {
    useAuth.mockReturnValue({
      user: { planStatus: null, plan: "free" },
    });
    render(<StripeTrialBanner onNavigate={vi.fn()} />);
    expect(
      screen.queryByTestId("stripe-trial-banner"),
    ).not.toBeInTheDocument();
  });

  it("does not render when user is null", () => {
    useAuth.mockReturnValue({ user: null });
    render(<StripeTrialBanner onNavigate={vi.fn()} />);
    expect(
      screen.queryByTestId("stripe-trial-banner"),
    ).not.toBeInTheDocument();
  });

  it("does not render when planStatus is past_due", () => {
    useAuth.mockReturnValue({
      user: { planStatus: "past_due", plan: "chatbot" },
    });
    render(<StripeTrialBanner onNavigate={vi.fn()} />);
    expect(
      screen.queryByTestId("stripe-trial-banner"),
    ).not.toBeInTheDocument();
  });

  it("shows day count and charge date when trialEnd is present ~3 days out", () => {
    // Set trialEnd to ~3 days from now (3 * 86400 * 1000 ms ahead)
    const trialEndMs = Date.now() + 3 * 86400 * 1000;
    const trialEndISO = new Date(trialEndMs).toISOString();
    useAuth.mockReturnValue({
      user: { planStatus: "trialing", plan: "growth", trialEnd: trialEndISO },
    });
    render(<StripeTrialBanner onNavigate={vi.fn()} />);

    // Day count: ceil((trialEndMs - now) / 86400000) = 3
    // Rendered text contains "3 day" (singular/plural handled by component)
    expect(screen.getByTestId("stripe-trial-banner")).toBeInTheDocument();
    const bannerText = screen.getByTestId("stripe-trial-banner").textContent;
    expect(bannerText).toMatch(/3 days? left in your free trial/i);

    // Charge date: formatted as "Mon D" (short month + day)
    const expectedDate = new Date(trialEndISO).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
    expect(bannerText).toContain(expectedDate);
  });

  it("shows generic copy when trialEnd is null (fallback)", () => {
    useAuth.mockReturnValue({
      user: { planStatus: "trialing", plan: "growth", trialEnd: null },
    });
    render(<StripeTrialBanner onNavigate={vi.fn()} />);
    expect(
      screen.getByText(/you're on a 7-day free trial/i),
    ).toBeInTheDocument();
  });
});
