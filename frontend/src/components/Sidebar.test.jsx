import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Sidebar from "./Sidebar";

let mockAuth;

vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

describe("Sidebar navigation (agent-first consolidation)", () => {
  beforeEach(() => {
    mockAuth = {
      logout: vi.fn(),
      user: {
        name: "Aidan",
        plan: "professional",
        role: "owner",
        businessType: "hvac",
      },
    };
  });

  // Contract updated 2026-06-10: the $49.99 Marketing Suite add-on was
  // retired - marketing is included with Growth+ and surfaced through Agent
  // OS, so the standalone marketing group and pages left the nav entirely.
  it("marketing add-on group and pages are gone from the nav", () => {
    render(
      <Sidebar currentPage="dashboard" onNavigate={vi.fn()} plan="professional" />,
    );

    expect(screen.queryByText("MARKETING ADD-ON")).not.toBeInTheDocument();
    for (const label of [
      "Marketing Dashboard",
      "Local SEO",
      "Social Media",
      "Campaigns",
      "A/B Tests",
      "Automation Rules",
      "Trigger Logs",
    ]) {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    }
  });

  // Contract updated 2026-06-10: the OPERATIONS group (Calendar, Invoices,
  // Documents) was retired from the nav - those jobs route through Agent OS.
  it("operations group and pages are gone from the nav", () => {
    render(
      <Sidebar currentPage="dashboard" onNavigate={vi.fn()} plan="professional" />,
    );

    expect(screen.queryByText("OPERATIONS")).not.toBeInTheDocument();
    for (const label of ["Calendar", "Invoices", "Documents"]) {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    }
  });

  it("retired pages stay out of the nav (their jobs route through Agent OS)", () => {
    render(
      <Sidebar currentPage="dashboard" onNavigate={vi.fn()} plan="professional" />,
    );

    for (const label of [
      "Content Studio",
      "Email Sequences",
      "Smart Lists",
      "Snippets",
      "Chat Flows",
      "Lead Scoring",
      "Bids",
    ]) {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    }
  });

  it("the core surfaces stay reachable", () => {
    render(
      <Sidebar currentPage="dashboard" onNavigate={vi.fn()} plan="professional" />,
    );

    // Collapsed groups render their items only after expansion.
    fireEvent.click(screen.getByText("SETTINGS"));

    for (const label of ["Agent OS", "Clients", "Conversations", "Billing"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });
});
