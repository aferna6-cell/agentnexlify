import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("../utils/api/_client", () => ({ BASE: "http://test" }));

import BotHealthPage from "./BotHealthPage";

function loopHealthPayload(over = {}) {
  return {
    generated_at: "2026-07-17T16:00:00+00:00",
    deliverables: {
      by_status: { pending_approval: 3, approved: 7, expired: 2 },
      pending_oldest_age_days: 2,
      expired_7d: 2,
    },
    suggestions: {
      by_status: { pending: 4, accepted: 6, superseded: 12 },
      pending_oldest_age_days: 1,
      filed_24h: 5,
      last_filed_at: "2026-07-17T06:00:00+00:00",
    },
    os_activity: { threads_7d: 9, runs_7d: 21 },
    bridges: { tenants_configured: 2, tenants_enabled: 1 },
    errors_7d: 0,
    ...over,
  };
}

beforeEach(() => {
  vi.spyOn(window, "prompt").mockReturnValue("test-secret");
  global.fetch = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetchOk(payload) {
  global.fetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => payload,
  });
}

describe("BotHealthPage", () => {
  it("renders the five vitals from the loop-health payload", async () => {
    mockFetchOk(loopHealthPayload());
    render(<BotHealthPage />);

    expect(await screen.findByText("Agent OS Loop Health")).toBeInTheDocument();
    expect(screen.getByText("Pending drafts")).toBeInTheDocument();
    // "3" renders in both the stat card and the breakdown table.
    expect(screen.getAllByText("3").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Suggestions queued")).toBeInTheDocument();
    expect(screen.getByText("OS threads (7d)")).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
    expect(screen.getByText("21 agent runs")).toBeInTheDocument();
    expect(screen.getByText("Bridges enabled")).toBeInTheDocument();
    expect(screen.getByText("2 tenant(s) configured")).toBeInTheDocument();
    expect(screen.getByText("Errors (7d)")).toBeInTheDocument();
  });

  it("renders status breakdown tables for deliverables and suggestions", async () => {
    mockFetchOk(loopHealthPayload());
    render(<BotHealthPage />);

    expect(
      await screen.findByText("Deliverables by status"),
    ).toBeInTheDocument();
    expect(screen.getByText("pending_approval")).toBeInTheDocument();
    expect(screen.getByText("Suggestions by status")).toBeInTheDocument();
    expect(screen.getByText("superseded")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("marks a failed section as unavailable while keeping the rest", async () => {
    mockFetchOk(loopHealthPayload({ deliverables: null }));
    render(<BotHealthPage />);

    expect(
      await screen.findByText(/Deliverables section unavailable/),
    ).toBeInTheDocument();
    expect(screen.getByText("Suggestions by status")).toBeInTheDocument();
  });

  it("shows the error state with a retry button when the fetch fails", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => "boom",
    });
    render(<BotHealthPage />);

    expect(
      await screen.findByText("Failed to load loop health"),
    ).toBeInTheDocument();
    expect(screen.getByText(/API 500/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("sends the admin secret header to the loop-health endpoint", async () => {
    mockFetchOk(loopHealthPayload());
    render(<BotHealthPage />);
    await screen.findByText("Agent OS Loop Health");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://test/api/v1/admin/loop-health",
      expect.objectContaining({
        headers: expect.objectContaining({ "x-api-secret": "test-secret" }),
      }),
    );
    // Rendered proof the authorized payload landed, not just the call shape.
    expect(screen.getByText(/Generated 2026-07-17T16:00:00/)).toBeInTheDocument();
  });
});
