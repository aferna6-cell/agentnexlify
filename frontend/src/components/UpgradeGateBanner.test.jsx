import "@testing-library/jest-dom/vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import UpgradeGateBanner from "./UpgradeGateBanner";

function fireGate(detail) {
  act(() => {
    window.dispatchEvent(
      new CustomEvent("anx:plan-upgrade-required", { detail }),
    );
  });
}

describe("UpgradeGateBanner", () => {
  it("renders nothing until a plan gate fires", () => {
    render(<UpgradeGateBanner />);
    expect(screen.queryByText("AGENT OS PLAN")).not.toBeInTheDocument();
  });

  it("shows the gate's message when the event fires", () => {
    render(<UpgradeGateBanner />);
    fireGate({
      error: "plan_upgrade_required",
      message: "The AI Workforce suite is part of the Agent OS plan.",
      upgrade_path: "/billing",
    });
    expect(screen.getByText("AGENT OS PLAN")).toBeInTheDocument();
    expect(
      screen.getByText(/AI Workforce suite is part of the Agent OS plan/),
    ).toBeInTheDocument();
  });

  it("falls back to a default message on an empty payload", () => {
    render(<UpgradeGateBanner />);
    fireGate({});
    expect(
      screen.getByText(/part of the Agent OS plan/),
    ).toBeInTheDocument();
  });

  it("navigates via onNavigate and hides", () => {
    const onNavigate = vi.fn();
    render(<UpgradeGateBanner onNavigate={onNavigate} />);
    fireGate({ message: "Upgrade please", upgrade_path: "/billing" });
    fireEvent.click(screen.getByText("See plans"));
    expect(onNavigate).toHaveBeenCalledWith("billing");
    expect(screen.queryByText("AGENT OS PLAN")).not.toBeInTheDocument();
  });

  it("dismiss hides the banner", () => {
    render(<UpgradeGateBanner />);
    fireGate({ message: "Upgrade please" });
    fireEvent.click(screen.getByText("Dismiss"));
    expect(screen.queryByText("AGENT OS PLAN")).not.toBeInTheDocument();
  });
});
