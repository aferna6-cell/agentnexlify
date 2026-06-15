import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import RequirePaid from "./RequirePaid";

// useAuth is swapped per-test via this mutable holder.
let mockAuth = { user: null, token: null };
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

// No Stripe-return params in these unit tests.
vi.mock("react-router-dom", () => ({
  useSearchParams: () => [{ get: () => null }],
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
