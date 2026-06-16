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
    // observable behavior — the navigation target — not a mock interaction.
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
});
