import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let mockAuth;
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("../utils/api/analytics", () => ({
  fetchAttribution: vi.fn(),
}));

import { fetchAttribution } from "../utils/api/analytics";
import AttributionPage from "./AttributionPage";

function attributionPayload(over = {}) {
  return {
    by_source: [
      { name: "google", count: 5 },
      { name: "(none)", count: 2 },
    ],
    by_medium: [
      { name: "cpc", count: 4 },
      { name: "(none)", count: 3 },
    ],
    by_campaign: [
      { name: "spring-promo", count: 4 },
      { name: "(none)", count: 3 },
    ],
    total: 7,
    attributed: 5,
    ...over,
  };
}

beforeEach(() => {
  mockAuth = { user: { tenantId: "ten1" }, token: "jwt" };
  fetchAttribution.mockReset();
});

describe("AttributionPage", () => {
  it("renders source, medium, and campaign breakdowns", async () => {
    fetchAttribution.mockResolvedValue(attributionPayload());
    render(<AttributionPage />);

    expect(await screen.findByText("Lead Attribution")).toBeInTheDocument();
    expect(screen.getByText("Leads by source")).toBeInTheDocument();
    expect(screen.getByText("Leads by medium")).toBeInTheDocument();
    expect(screen.getByText("Campaigns")).toBeInTheDocument();
    expect(screen.getByText("spring-promo")).toBeInTheDocument();
    expect(screen.getByText("5 of 7 leads attributed", { exact: false })).toBeInTheDocument();
    expect(fetchAttribution).toHaveBeenCalledWith("ten1", "jwt");
  });

  it("shows the helpful empty state when the tenant has no leads", async () => {
    fetchAttribution.mockResolvedValue(
      attributionPayload({
        by_source: [],
        by_medium: [],
        by_campaign: [],
        total: 0,
        attributed: 0,
      }),
    );
    render(<AttributionPage />);

    expect(await screen.findByText("No leads yet")).toBeInTheDocument();
    expect(
      screen.getByText(/utm_source/, { exact: false }),
    ).toBeInTheDocument();
  });

  it("shows the error state with retry when the fetch fails", async () => {
    fetchAttribution.mockRejectedValue(new Error("network down"));
    render(<AttributionPage />);

    expect(
      await screen.findByText("Failed to load attribution"),
    ).toBeInTheDocument();
    expect(screen.getByText("network down")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
