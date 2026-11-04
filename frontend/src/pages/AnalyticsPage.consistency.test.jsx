import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ user: { tenantId: "ten-1" }, token: "tok" }),
}));

vi.mock("../utils/api/analytics", () => ({
  fetchAnalyticsOverview: vi.fn().mockResolvedValue({
    total_conversations: 4,
    leads_all_time: 2,
    total_leads: 0,
    conversion_rate: 0,
    total_appointments: 0,
    changes: {
      conversations: 0,
      leads: 0,
      conversion_rate: 0,
      appointments: 0,
    },
  }),
  fetchAnalyticsConversations: vi.fn().mockResolvedValue({ data: [] }),
  fetchAnalyticsLeads: vi.fn().mockResolvedValue({ daily: [], by_stage: {} }),
  fetchAnalyticsResponseTimes: vi.fn().mockResolvedValue({}),
  fetchAnalyticsWidget: vi.fn().mockResolvedValue({ peak_hours: [] }),
  fetchMissedCallAnalytics: vi.fn().mockResolvedValue({}),
  fetchLeadSources: vi.fn().mockResolvedValue({}),
  fetchAnalyticsSnapshot: vi.fn(),
}));

vi.mock("../utils/api/conversations", () => ({
  fetchConversations: vi.fn().mockResolvedValue({ conversations: [] }),
}));

vi.mock("../utils/api/tags", () => ({
  fetchTagDefinitions: vi.fn().mockResolvedValue([]),
}));

import AnalyticsPage from "./AnalyticsPage";

describe("Analytics headline definitions", () => {
  it("defaults to this month and shows the all-time lead stock", async () => {
    render(<AnalyticsPage />);
    expect(
      await screen.findByRole("button", { name: "This month" }),
    ).toBeTruthy();
    expect(await screen.findByText("All time")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
  });
});
