import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import UsageUpgradeNudge from "./UsageUpgradeNudge";

const TID = "usage-upgrade-nudge";

describe("UsageUpgradeNudge", () => {
  it("does not render below the 80% near threshold", () => {
    render(
      <UsageUpgradeNudge
        usage={{ plan: "chatbot", agent_runs: 79, cap: 100, percent: 79, cap_reached: false }}
      />,
    );
    expect(screen.queryByTestId(TID)).not.toBeInTheDocument();
  });

  it("renders at exactly 80% (near threshold, inclusive)", () => {
    render(
      <UsageUpgradeNudge
        usage={{ plan: "chatbot", agent_runs: 80, cap: 100, percent: 80, cap_reached: false }}
      />,
    );
    expect(screen.getByTestId(TID)).toBeInTheDocument();
    // States the real usage vs limit (no invented numbers).
    expect(screen.getByText(/80 of 100 agent runs/i)).toBeInTheDocument();
    // States the concrete upgrade benefit.
    expect(screen.getByText(/Agent OS for 2,000 runs a month/i)).toBeInTheDocument();
  });

  it("renders the at-cap message when cap_reached is true", () => {
    render(
      <UsageUpgradeNudge
        usage={{ plan: "free", agent_runs: 25, cap: 25, percent: 100, cap_reached: true }}
      />,
    );
    expect(screen.getByTestId(TID)).toBeInTheDocument();
    expect(
      screen.getByText(/used all your agent runs this month/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/25 of 25 agent runs/i)).toBeInTheDocument();
  });

  it("does not render when already on the top plan (agent_os)", () => {
    render(
      <UsageUpgradeNudge
        usage={{ plan: "agent_os", agent_runs: 1999, cap: 2000, percent: 100, cap_reached: false }}
      />,
    );
    expect(screen.queryByTestId(TID)).not.toBeInTheDocument();
  });

  it("does not render when usage is missing", () => {
    render(<UsageUpgradeNudge usage={null} />);
    expect(screen.queryByTestId(TID)).not.toBeInTheDocument();
  });

  it("navigates to billing when View plans is clicked", () => {
    let navigatedTo = null;
    render(
      <UsageUpgradeNudge
        usage={{ plan: "chatbot", agent_runs: 95, cap: 100, percent: 95, cap_reached: false }}
        onNavigate={(key) => {
          navigatedTo = key;
        }}
      />,
    );
    expect(navigatedTo).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /view plans/i }));
    expect(navigatedTo).toBe("billing");
  });

  it("dismisses and never blocks the app", () => {
    render(
      <UsageUpgradeNudge
        usage={{ plan: "chatbot", agent_runs: 90, cap: 100, percent: 90, cap_reached: false }}
      />,
    );
    expect(screen.getByTestId(TID)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(screen.queryByTestId(TID)).not.toBeInTheDocument();
  });

  it("derives percent from agent_runs/cap when percent is absent", () => {
    render(
      <UsageUpgradeNudge
        usage={{ plan: "chatbot", agent_runs: 90, cap: 100, cap_reached: false }}
      />,
    );
    expect(screen.getByTestId(TID)).toBeInTheDocument();
    expect(screen.getByText(/\(90%\)/)).toBeInTheDocument();
  });
});
