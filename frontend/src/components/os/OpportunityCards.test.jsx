import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  listOsBacklog: vi.fn(),
  decideOsBacklog: vi.fn(),
}));

vi.mock("../../utils/notify", () => ({
  notify: { success: vi.fn(), error: vi.fn() },
}));

import { listOsBacklog, decideOsBacklog } from "../../utils/api/os";
import { notify } from "../../utils/notify";
import OpportunityCards from "./OpportunityCards";

const PENDING = {
  id: "req-1",
  status: "pending",
  summary: "5 leads went cold this week - want me to follow up?",
  detail: "Accept and I'll draft a friendly check-in for each.",
};
const DECIDED = {
  id: "req-2",
  status: "accepted",
  summary: "old accepted card",
};
const SUPERSEDED = {
  id: "req-3",
  status: "superseded",
  summary: "3 leads went cold this week - want me to follow up?",
};

beforeEach(() => {
  listOsBacklog.mockReset().mockResolvedValue([]);
  decideOsBacklog.mockReset();
  notify.success.mockReset();
  notify.error.mockReset();
});

describe("OpportunityCards", () => {
  it("renders pending cards with summary and detail", async () => {
    listOsBacklog.mockResolvedValue([PENDING, DECIDED, SUPERSEDED]);
    render(<OpportunityCards token="jwt" />);

    expect(
      await screen.findByText("5 leads went cold this week - want me to follow up?"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Accept and I'll draft a friendly check-in for each."),
    ).toBeInTheDocument();
    // Decided + superseded rows never render as actionable cards.
    expect(screen.queryByText("old accepted card")).not.toBeInTheDocument();
    expect(
      screen.queryByText("3 leads went cold this week - want me to follow up?"),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/spotted 1 opportunity$/i)).toBeInTheDocument();
  });

  it("renders nothing when there are no actionable cards", async () => {
    listOsBacklog.mockResolvedValue([DECIDED]);
    const { container } = render(<OpportunityCards token="jwt" />);
    await waitFor(() => expect(listOsBacklog).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the fetch fails", async () => {
    listOsBacklog.mockRejectedValue(new Error("boom"));
    const { container } = render(<OpportunityCards token="jwt" />);
    await waitFor(() => expect(listOsBacklog).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("accept decides 'accepted', removes the card, and confirms drafts", async () => {
    listOsBacklog.mockResolvedValue([PENDING]);
    decideOsBacklog.mockResolvedValue({ id: "req-1", status: "accepted" });
    render(<OpportunityCards token="jwt" />);

    fireEvent.click(await screen.findByRole("button", { name: "Accept" }));

    await waitFor(() =>
      expect(decideOsBacklog).toHaveBeenCalledWith("jwt", "req-1", {
        decision: "accepted",
      }),
    );
    await waitFor(() =>
      expect(
        screen.queryByText("5 leads went cold this week - want me to follow up?"),
      ).not.toBeInTheDocument(),
    );
    expect(notify.success).toHaveBeenCalledWith(
      expect.stringContaining("approvals"),
    );
  });

  it("dismiss decides 'declined' and removes the card", async () => {
    listOsBacklog.mockResolvedValue([PENDING]);
    decideOsBacklog.mockResolvedValue({ id: "req-1", status: "declined" });
    render(<OpportunityCards token="jwt" />);

    fireEvent.click(await screen.findByRole("button", { name: "Dismiss" }));

    await waitFor(() =>
      expect(decideOsBacklog).toHaveBeenCalledWith("jwt", "req-1", {
        decision: "declined",
      }),
    );
    await waitFor(() =>
      expect(
        screen.queryByText("5 leads went cold this week - want me to follow up?"),
      ).not.toBeInTheDocument(),
    );
    expect(notify.success).toHaveBeenCalledWith("Dismissed");
  });

  it("keeps the card and surfaces the error when the decision fails", async () => {
    listOsBacklog.mockResolvedValue([PENDING]);
    decideOsBacklog.mockRejectedValue(new Error("Owner role required"));
    render(<OpportunityCards token="jwt" />);

    fireEvent.click(await screen.findByRole("button", { name: "Accept" }));

    await waitFor(() =>
      expect(notify.error).toHaveBeenCalledWith("Owner role required"),
    );
    expect(
      screen.getByText("5 leads went cold this week - want me to follow up?"),
    ).toBeInTheDocument();
  });
});
