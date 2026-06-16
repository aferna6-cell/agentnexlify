import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import RequirePaid from "./RequirePaid";

// useAuth is swapped per-test via this mutable holder.
let mockAuth = { user: null, token: null };
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

// useSearchParams is swapped per-test via this mutable holder. Default: no
// Stripe-return params (get always returns null).
let mockSearch = { get: () => null };
vi.mock("react-router-dom", () => ({
  useSearchParams: () => [mockSearch],
}));

const Child = () => <div>DASHBOARD_CHILD</div>;

function renderWith(auth) {
  mockAuth = auth;
  return render(
    <RequirePaid>
      <Child />
    </RequirePaid>,
  );
}

const GATE = "Choose your plan to continue";

beforeEach(() => {
  mockSearch = { get: () => null };
});

describe("RequirePaid pay-gate (fail-open)", () => {
  it("renders children when logged out (downstream handles login)", () => {
    renderWith({ user: null, token: null });
    expect(screen.getByText("DASHBOARD_CHILD")).toBeTruthy();
    expect(screen.queryByText(GATE)).toBeNull();
  });

  it("renders children while plan unknown (/me not yet resolved)", () => {
    // user present from JWT but payGateExempt/planStatus undefined → fail open
    renderWith({ user: { tenantId: "t1" }, token: "jwt" });
    expect(screen.getByText("DASHBOARD_CHILD")).toBeTruthy();
    expect(screen.queryByText(GATE)).toBeNull();
  });

  it("renders children for a grandfathered (exempt) tenant", () => {
    renderWith({
      user: { tenantId: "t1", payGateExempt: true, planStatus: null },
      token: "jwt",
    });
    expect(screen.getByText("DASHBOARD_CHILD")).toBeTruthy();
    expect(screen.queryByText(GATE)).toBeNull();
  });

  it("renders children for an active plan", () => {
    renderWith({
      user: { tenantId: "t1", payGateExempt: false, planStatus: "active" },
      token: "jwt",
    });
    expect(screen.getByText("DASHBOARD_CHILD")).toBeTruthy();
  });

  it("shows the checkout gate for a known unpaid, non-exempt tenant", () => {
    renderWith({
      user: { tenantId: "t1", payGateExempt: false, planStatus: null },
      token: "jwt",
    });
    expect(screen.getByText(GATE)).toBeTruthy();
    expect(screen.queryByText("DASHBOARD_CHILD")).toBeNull();
  });
});

describe("RequirePaid Stripe-return webhook race", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("polls /me with backoff and unlocks once the webhook lands", async () => {
    // Stripe just redirected back: session_id present. The tenant looks unpaid
    // on the first /me reads (webhook not landed yet), then flips to active.
    mockSearch = { get: (k) => (k === "session_id" ? "cs_test_123" : null) };

    let call = 0;
    const responses = [
      { plan_status: null, pay_gate_exempt: false }, // webhook not landed
      { plan_status: null, pay_gate_exempt: false }, // still not landed
      { plan_status: "active", pay_gate_exempt: false }, // webhook landed
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => responses[Math.min(call++, responses.length - 1)],
      })),
    );

    vi.useFakeTimers();
    renderWith({
      user: { tenantId: "t1", payGateExempt: false, planStatus: null },
      token: "jwt",
    });

    // While polling, the gate must NOT show (we show "Verifying payment...").
    expect(screen.queryByText(GATE)).toBeNull();

    // Drain the backoff timers + their awaited fetches.
    await vi.runAllTimersAsync();
    vi.useRealTimers();

    await waitFor(() => expect(screen.getByText("DASHBOARD_CHILD")).toBeTruthy());
    expect(screen.queryByText(GATE)).toBeNull();
    // Polled more than once - proves it didn't give up on the first unpaid read.
    expect(call).toBeGreaterThan(1);
  });
});
