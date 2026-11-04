import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const disconnectGoogleCalendar = vi.fn(() => Promise.resolve({}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { tenantId: "tenant-1", role: "owner" },
    token: "token",
  }),
}));

vi.mock("../utils/api/webhooks", () => ({
  fetchWebhooks: vi.fn(() => Promise.resolve([])),
  createWebhook: vi.fn(),
  updateWebhook: vi.fn(),
  toggleWebhook: vi.fn(),
  deleteWebhook: vi.fn(),
  fetchWebhookLogs: vi.fn(() => Promise.resolve([])),
  testWebhook: vi.fn(),
}));

vi.mock("../utils/api/connectors", () => ({
  fetchConnectorsStatus: vi.fn(() => Promise.resolve({ connectors: [] })),
}));

vi.mock("../utils/api/integrations", () => ({
  fetchGoogleCalendarStatus: vi.fn(() =>
    Promise.resolve({ connected: true, email: "owner@example.com" }),
  ),
  startGoogleCalendarAuth: vi.fn(),
  disconnectGoogleCalendar: (...args) => disconnectGoogleCalendar(...args),
  fetchM365CalendarStatus: vi.fn(() => Promise.resolve({ connected: false })),
  startM365CalendarAuth: vi.fn(),
  disconnectM365Calendar: vi.fn(),
  fetchHubSpotStatus: vi.fn(() => Promise.resolve({ connected: false })),
  startHubSpotAuth: vi.fn(),
  disconnectHubSpot: vi.fn(),
  fetchFacebookStatus: vi.fn(() => Promise.resolve({ connected: false })),
  getFacebookAuthUrl: vi.fn(),
  disconnectFacebook: vi.fn(),
  fetchInstagramStatus: vi.fn(() => Promise.resolve({ connected: false })),
  getInstagramAuthUrl: vi.fn(),
  disconnectInstagram: vi.fn(),
  fetchBridgeConfig: vi.fn(() => Promise.resolve(null)),
  toggleBridge: vi.fn(),
  saveBridgeConfig: vi.fn(),
  startGmailAuth: vi.fn(),
  fetchGmailStatus: vi.fn(() => Promise.resolve({ connected: false })),
  disconnectGmail: vi.fn(),
}));

import IntegrationsPage from "./IntegrationsPage";

describe("Google Calendar disconnect confirmation", () => {
  beforeEach(() => {
    disconnectGoogleCalendar.mockClear();
  });

  it("asks before disconnecting and does nothing on cancel", async () => {
    render(<IntegrationsPage />);
    const disconnect = await screen.findByRole("button", {
      name: "Disconnect",
    });
    fireEvent.click(disconnect);

    expect(
      screen.getByRole("alertdialog", { name: "Disconnect Google Calendar" }),
    ).toHaveTextContent(/removes the stored connection/i);
    expect(disconnectGoogleCalendar).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(
      screen.queryByRole("alertdialog", { name: "Disconnect Google Calendar" }),
    ).not.toBeInTheDocument();
    expect(disconnectGoogleCalendar).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Disconnect" }),
    ).toBeInTheDocument();
  });

  it("disconnects only after the confirmation click", async () => {
    render(<IntegrationsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Disconnect" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Confirm disconnect?" }),
    );

    await waitFor(() => {
      expect(disconnectGoogleCalendar).toHaveBeenCalledWith(
        "tenant-1",
        "token",
      );
    });
  });
});
