import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Sidebar from "./Sidebar";

let mockAuth;

vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

describe("Sidebar marketing navigation", () => {
  beforeEach(() => {
    mockAuth = {
      logout: vi.fn(),
      user: {
        name: "Aidan",
        plan: "professional",
        role: "owner",
        businessType: "hvac",
        marketing_addon_active: false,
      },
    };
  });

  it("keeps the full marketing suite visible even before addon activation", () => {
    render(
      <Sidebar currentPage="dashboard" onNavigate={vi.fn()} plan="professional" />,
    );

    fireEvent.click(screen.getByText("MARKETING"));

    for (const label of [
      "Content Studio",
      "Marketing Dashboard",
      "Local SEO",
      "Social Media",
      "Campaigns",
      "A/B Tests",
      "Automation Rules",
      "Trigger Logs",
      "Email Sequences",
      "Forms",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });
});
