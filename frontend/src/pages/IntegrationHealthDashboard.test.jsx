import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let mockAuth;
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("../utils/api/widgetHealth", () => ({
  getWidgetHealth: vi.fn(),
  updateAllowedDomains: vi.fn(),
}));

vi.mock("../components/SkeletonLoader", () => ({
  default: () => <div data-testid="skeleton" />,
}));

import {
  getWidgetHealth,
  updateAllowedDomains,
} from "../utils/api/widgetHealth";
import IntegrationHealthDashboard from "./IntegrationHealthDashboard";

function healthPayload(over = {}) {
  return {
    overall: "healthy",
    checks: [
      { id: "c1", label: "Widget installed", status: "ok", detail: "Found on site" },
      {
        id: "c2",
        label: "Domain allowed",
        status: "warn",
        detail: "No domains set",
        action: { label: "Configure", target: "settings" },
      },
    ],
    stats: { leads_7d: 12, conversations_7d: 34, appointments_7d: 5 },
    allowed_domains: ["example.com"],
    ...over,
  };
}

beforeEach(() => {
  mockAuth = { user: { tenantId: "ten1" }, token: "jwt" };
  getWidgetHealth.mockReset();
  updateAllowedDomains.mockReset();
});

describe("IntegrationHealthDashboard", () => {
  it("shows the skeleton while loading", () => {
    getWidgetHealth.mockReturnValue(new Promise(() => {}));
    render(<IntegrationHealthDashboard />);
    expect(screen.getByTestId("skeleton")).toBeInTheDocument();
  });

  it("renders banner, stats, and checks after load", async () => {
    getWidgetHealth.mockResolvedValue(healthPayload());
    render(<IntegrationHealthDashboard />);

    expect(await screen.findByText("You're live")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("34")).toBeInTheDocument();
    expect(screen.getByText("Widget installed")).toBeInTheDocument();
    expect(screen.getByText("Domain allowed")).toBeInTheDocument();
    expect(getWidgetHealth).toHaveBeenCalledWith("ten1", "jwt");
  });

  it("fires onNavigate from a check action button", async () => {
    getWidgetHealth.mockResolvedValue(healthPayload());
    const onNavigate = vi.fn();
    render(<IntegrationHealthDashboard onNavigate={onNavigate} />);

    fireEvent.click(await screen.findByRole("button", { name: "Configure" }));
    expect(onNavigate).toHaveBeenCalledWith("settings");
  });

  it("shows a retry path when the load fails", async () => {
    getWidgetHealth.mockRejectedValueOnce(new Error("boom"));
    render(<IntegrationHealthDashboard />);
    expect(await screen.findByText("boom")).toBeInTheDocument();

    getWidgetHealth.mockResolvedValueOnce(healthPayload());
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("You're live")).toBeInTheDocument();
  });

  it("adds a domain and saves the full list", async () => {
    getWidgetHealth.mockResolvedValue(healthPayload({ allowed_domains: [] }));
    updateAllowedDomains.mockResolvedValue({ allowed_domains: ["new.com"] });

    render(<IntegrationHealthDashboard />);
    await screen.findByText("You're live");

    fireEvent.change(screen.getByPlaceholderText("example.com"), {
      target: { value: "New.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(updateAllowedDomains).toHaveBeenCalledWith("ten1", "jwt", [
        "new.com",
      ]),
    );
    expect(await screen.findByText("Allowed domains saved.")).toBeInTheDocument();
  });

  it("removes a domain chip", async () => {
    getWidgetHealth.mockResolvedValue(
      healthPayload({ allowed_domains: ["example.com"] }),
    );
    render(<IntegrationHealthDashboard />);
    await screen.findByText("You're live");

    expect(screen.getByText("example.com")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove example.com" }));
    expect(screen.queryByText("example.com")).not.toBeInTheDocument();
  });
});
