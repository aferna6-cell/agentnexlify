import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, it, vi } from "vitest";

import DemoBanner from "./DemoBanner";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../context/AuthContext";

describe("DemoBanner", () => {
  it("renders when user.role is demo", () => {
    useAuth.mockReturnValue({
      user: { role: "demo", tenantId: "demo-tenant-1" },
    });
    render(<DemoBanner />);
    expect(screen.getByTestId("demo-banner")).toBeInTheDocument();
    expect(
      screen.getByText(/explore everything, data resets nightly/i),
    ).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: /start your free account/i });
    expect(cta).toBeInTheDocument();
    expect(cta).toHaveAttribute("href", "/signup");
  });

  it("does not render when user.role is owner", () => {
    useAuth.mockReturnValue({
      user: { role: "owner", tenantId: "tenant-abc" },
    });
    render(<DemoBanner />);
    expect(screen.queryByTestId("demo-banner")).not.toBeInTheDocument();
  });

  it("does not render when user is null", () => {
    useAuth.mockReturnValue({ user: null });
    render(<DemoBanner />);
    expect(screen.queryByTestId("demo-banner")).not.toBeInTheDocument();
  });
});
