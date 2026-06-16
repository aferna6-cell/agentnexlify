import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, vi, expect, afterEach } from "vitest";

import PaymentRecoveryGate, { RECOVERY_STATUSES } from "./PaymentRecoveryGate";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("PaymentRecoveryGate", () => {
  it("renders the payment-failed recovery prompt", () => {
    render(<PaymentRecoveryGate tenantId="t1" token="tok" />);
    expect(screen.getByTestId("payment-recovery-gate")).toBeInTheDocument();
    expect(
      screen.getByText(/your payment didn't go through/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /update payment method/i }),
    ).toBeInTheDocument();
  });

  it("shows an error message when the portal call fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "No billing account." }),
    });
    render(<PaymentRecoveryGate tenantId="t1" token="tok" />);
    fireEvent.click(
      screen.getByRole("button", { name: /update payment method/i }),
    );
    expect(await screen.findByText(/no billing account/i)).toBeInTheDocument();
  });

  it("redirects to the Stripe portal URL on success", async () => {
    // jsdom: replace location so assigning href is observable, not a navigation.
    const originalLocation = window.location;
    delete window.location;
    window.location = { href: "" };
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ portal_url: "https://billing.stripe.com/p/abc" }),
    });

    render(<PaymentRecoveryGate tenantId="t1" token="tok" />);
    fireEvent.click(
      screen.getByRole("button", { name: /update payment method/i }),
    );

    await waitFor(() =>
      expect(window.location.href).toBe("https://billing.stripe.com/p/abc"),
    );
    window.location = originalLocation;
  });

  it("treats only post-subscription statuses as recovery", () => {
    expect(RECOVERY_STATUSES.has("past_due")).toBe(true);
    expect(RECOVERY_STATUSES.has("paused")).toBe(true);
    expect(RECOVERY_STATUSES.has("unpaid")).toBe(true);
    expect(RECOVERY_STATUSES.has("trialing")).toBe(false);
    expect(RECOVERY_STATUSES.has("active")).toBe(false);
  });
});
