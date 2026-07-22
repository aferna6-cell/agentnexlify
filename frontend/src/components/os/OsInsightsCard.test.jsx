import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  fetchOsInsights: vi.fn(),
}));

import { fetchOsInsights } from "../../utils/api/os";
import OsInsightsCard from "./OsInsightsCard";

// The card loads insights via the shared api layer (audit M5); stub it.
function stubInsights(payload) {
  fetchOsInsights.mockResolvedValue(payload);
}

const IDLE_WEEK = {
  leads_captured: 0,
  appointments_booked: 0,
  invoices_sent: 0,
  agent_runs_completed: 0,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("OsInsightsCard cold-start starters", () => {
  it("renders starter chips for an idle tenant instead of hiding", async () => {
    stubInsights({
      week: IDLE_WEEK,
      suggestions: [],
      starters: [
        { label: "Ask happy customers for reviews", prompt: "Write a review ask." },
        { label: "Draft a promo message", prompt: "Draft a promo." },
      ],
    });
    render(<OsInsightsCard token="jwt" onSuggestion={vi.fn()} />);
    expect(await screen.findByTestId("starter-tasks")).toBeInTheDocument();
    expect(screen.getByText("Put your AI staff to work")).toBeInTheDocument();
    expect(screen.getByText("Ask happy customers for reviews")).toBeInTheDocument();
  });

  it("clicking a starter fills the composer with its prompt", async () => {
    const onSuggestion = vi.fn();
    stubInsights({
      week: IDLE_WEEK,
      suggestions: [],
      starters: [{ label: "Draft a promo message", prompt: "Draft a promo." }],
    });
    render(<OsInsightsCard token="jwt" onSuggestion={onSuggestion} />);
    const chip = await screen.findByText("Draft a promo message");
    expect(chip).toBeInTheDocument();
    fireEvent.click(chip);
    expect(onSuggestion).toHaveBeenCalledWith("Draft a promo.");
  });

  it("still hides entirely when idle and the backend sends no starters (back-compat)", async () => {
    stubInsights({ week: IDLE_WEEK, suggestions: [] });
    const { container } = render(
      <OsInsightsCard token="jwt" onSuggestion={vi.fn()} />,
    );
    await waitFor(() => expect(fetchOsInsights).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("active tenants keep the weekly recap and get no starter strip", async () => {
    stubInsights({
      week: { ...IDLE_WEEK, leads_captured: 3, agent_runs_completed: 2 },
      suggestions: [],
      starters: [],
    });
    render(<OsInsightsCard token="jwt" onSuggestion={vi.fn()} />);
    expect(await screen.findByText("Your AI staff this week")).toBeInTheDocument();
    expect(screen.queryByTestId("starter-tasks")).toBeNull();
  });
});
