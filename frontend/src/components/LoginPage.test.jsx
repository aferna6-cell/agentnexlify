import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

const login = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ login }),
}));

import LoginPage from "./LoginPage";

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="loc">{location.pathname}</div>;
}

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

function fillAndSubmit() {
  fireEvent.change(screen.getByPlaceholderText("you@company.com"), {
    target: { value: "owner@example.com" },
  });
  fireEvent.change(screen.getByPlaceholderText("Enter password"), {
    target: { value: "secret-pass" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
}

beforeEach(() => {
  login.mockReset();
  vi.stubGlobal("fetch", vi.fn());
});

describe("LoginPage redirect", () => {
  it("replaces /login with /dashboard after a successful sign-in", async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ token: "jwt-token", tenant_id: "ten-1" }),
    });
    renderLogin();
    fillAndSubmit();

    await waitFor(() => {
      expect(screen.getByTestId("loc")).toHaveTextContent("/dashboard");
    });
    expect(login).toHaveBeenCalledWith("jwt-token");
    expect(screen.queryByText("jwt-token")).not.toBeInTheDocument();
  });

  it("stays on the login form when credentials are rejected", async () => {
    fetch.mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Invalid credentials" }),
    });
    renderLogin();
    fillAndSubmit();

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
    expect(screen.queryByTestId("loc")).not.toBeInTheDocument();
  });

  it("does not navigate when the network request fails", async () => {
    fetch.mockRejectedValue(new Error("offline"));
    renderLogin();
    fillAndSubmit();

    expect(await screen.findByText("offline")).toBeInTheDocument();
    expect(screen.queryByTestId("loc")).not.toBeInTheDocument();
  });
});
