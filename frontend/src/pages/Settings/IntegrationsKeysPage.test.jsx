import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock AuthContext before importing anything that uses it
let mockAuth;
vi.mock("../../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

// Mock the integrationKeys module
vi.mock("../../utils/api/integrationKeys", () => ({
  listIntegrationKeys: vi.fn(),
  saveIntegrationKey: vi.fn(),
  verifyIntegrationKey: vi.fn(),
  deleteIntegrationKey: vi.fn(),
}));

import {
  listIntegrationKeys,
  saveIntegrationKey,
  verifyIntegrationKey,
  deleteIntegrationKey,
} from "../../utils/api/integrationKeys";

import IntegrationsKeysPage from "./IntegrationsKeysPage";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeKeyList(overrides = []) {
  const defaults = [
    {
      provider: "stripe",
      health: "green",
      detail: "Verified",
      last_verified_at: "2026-06-10T12:00:00Z",
      masked_key: "sk_live_****abcd",
    },
    {
      provider: "twilio",
      health: "yellow",
      detail: "Rate limit warning",
      last_verified_at: "2026-06-09T08:00:00Z",
      masked_key: "AC****1234",
    },
    {
      provider: "resend",
      health: "red",
      detail: "Invalid key",
      last_verified_at: null,
      masked_key: "re_****5678",
    },
  ];
  return overrides.length ? overrides : defaults;
}

// ApiError-like stub (status + body)
function makeApiError(status, detail) {
  const err = new Error(detail);
  err.status = status;
  err.body = { detail };
  return err;
}

beforeEach(() => {
  mockAuth = { token: "test-token" };
  listIntegrationKeys.mockReset();
  saveIntegrationKey.mockReset();
  verifyIntegrationKey.mockReset();
  deleteIntegrationKey.mockReset();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("IntegrationsKeysPage", () => {
  it("shows loading indicator then renders three provider cards", async () => {
    listIntegrationKeys.mockResolvedValue(makeKeyList());
    render(<IntegrationsKeysPage />);

    // Initial loading text is present
    expect(screen.getByText(/Loading integration keys/i)).toBeInTheDocument();

    // After data loads, all three providers render
    expect(await screen.findByText("Stripe")).toBeInTheDocument();
    expect(screen.getByText("Twilio")).toBeInTheDocument();
    expect(screen.getByText("Resend")).toBeInTheDocument();
  });

  it("renders the masked key and health pill for each configured provider", async () => {
    listIntegrationKeys.mockResolvedValue(makeKeyList());
    render(<IntegrationsKeysPage />);

    await screen.findByText("Stripe");

    expect(screen.getByText("sk_live_****abcd")).toBeInTheDocument();
    expect(screen.getByText("AC****1234")).toBeInTheDocument();
    expect(screen.getByText("re_****5678")).toBeInTheDocument();

    // Health pills (label text from HEALTH_PILL map)
    const healthyPills = screen.getAllByText("Healthy");
    expect(healthyPills.length).toBeGreaterThanOrEqual(1);
  });

  it("clicking Verify updates the health pill via verifyIntegrationKey", async () => {
    listIntegrationKeys.mockResolvedValue(makeKeyList());
    verifyIntegrationKey.mockResolvedValue({
      health: "green",
      detail: "All checks passed",
    });

    render(<IntegrationsKeysPage />);
    await screen.findByText("Stripe");

    // Find the first Verify button (Stripe card)
    const verifyButtons = screen.getAllByRole("button", { name: /verify/i });
    fireEvent.click(verifyButtons[0]);

    await waitFor(() =>
      expect(verifyIntegrationKey).toHaveBeenCalledWith("stripe", "test-token"),
    );

    // Observable behavior: the verify result detail renders in the card
    expect(await screen.findByText(/All checks passed/i)).toBeInTheDocument();
    expect(verifyIntegrationKey).toHaveBeenCalledTimes(1);
  });

  it("Remove on a 409 shows the active-subscription inline message", async () => {
    listIntegrationKeys.mockResolvedValue(makeKeyList());
    deleteIntegrationKey.mockRejectedValue(
      makeApiError(409, "Active subscription exists"),
    );

    render(<IntegrationsKeysPage />);
    await screen.findByText("Stripe");

    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    fireEvent.click(removeButtons[0]);

    expect(
      await screen.findByText(
        /Cannot remove - active Stripe subscription\. Cancel\/migrate the subscription first\./i,
      ),
    ).toBeInTheDocument();
  });

  it("Remove on a non-409 error shows a generic error message", async () => {
    listIntegrationKeys.mockResolvedValue(makeKeyList());
    deleteIntegrationKey.mockRejectedValue(makeApiError(500, "Server error"));

    render(<IntegrationsKeysPage />);
    await screen.findByText("Twilio");

    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    // Click second remove button (Twilio)
    fireEvent.click(removeButtons[1]);

    expect(await screen.findByText(/Server error/i)).toBeInTheDocument();
  });

  it("save flow: clicking Edit key, typing, and saving calls saveIntegrationKey", async () => {
    listIntegrationKeys.mockResolvedValue(makeKeyList());
    saveIntegrationKey.mockResolvedValue({
      saved: true,
      verified: true,
      masked: "re_****newkey",
    });
    // After save, a fresh list is fetched
    listIntegrationKeys
      .mockResolvedValueOnce(makeKeyList()) // initial load
      .mockResolvedValueOnce(makeKeyList()); // post-save refresh

    render(<IntegrationsKeysPage />);
    await screen.findByText("Resend");

    const editButtons = screen.getAllByRole("button", { name: /edit key/i });
    // Resend is the third card - click its Edit
    fireEvent.click(editButtons[editButtons.length - 1]);

    const input = screen.getByPlaceholderText(/Paste your Resend secret key/i);
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "re_live_supersecret" } });

    const saveButtons = screen.getAllByRole("button", { name: /^Save$/i });
    fireEvent.click(saveButtons[0]);

    await waitFor(() =>
      expect(saveIntegrationKey).toHaveBeenCalledWith(
        "resend",
        "re_live_supersecret",
        {},
        "test-token",
      ),
    );
  });

  it("shows error state with retry button when listIntegrationKeys fails", async () => {
    listIntegrationKeys.mockRejectedValueOnce(
      makeApiError(500, "Service unavailable"),
    );
    render(<IntegrationsKeysPage />);

    expect(
      await screen.findByText(/Service unavailable/i),
    ).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: /retry/i });
    expect(retryBtn).toBeInTheDocument();

    // Retry succeeds
    listIntegrationKeys.mockResolvedValueOnce(makeKeyList());
    fireEvent.click(retryBtn);

    expect(await screen.findByText("Stripe")).toBeInTheDocument();
  });

  it("shows empty state when no keys are configured", async () => {
    listIntegrationKeys.mockResolvedValue([]);
    render(<IntegrationsKeysPage />);

    await screen.findByText("Stripe"); // provider labels still show
    expect(
      screen.getByText(/No integration keys saved yet/i),
    ).toBeInTheDocument();
  });
});
