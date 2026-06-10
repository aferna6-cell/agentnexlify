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
        marketing_addon_active: false,
      },
    };
  });

  // Contract updated 2026-06-09: the standalone marketing pages that agents
  // now handle (Content Studio, Email Sequences, Forms, ...) were retired
  // from the nav. What remains is the PAID marketing add-on set, which must
  // stay discoverable before activation (upsell path) under its own group.
  it("keeps the paid marketing add-on discoverable before activation", () => {
    render(
      <Sidebar currentPage="dashboard" onNavigate={vi.fn()} plan="professional" />,
    );

    fireEvent.click(screen.getByText("MARKETING ADD-ON"));

    for (const label of [
      "Marketing Dashboard",
      "Local SEO",
      "Social Media",
      "Campaigns",
      "A/B Tests",
      "Automation Rules",
      "Trigger Logs",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
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
    fireEvent.click(screen.getByText("OPERATIONS"));
    fireEvent.click(screen.getByText("SETTINGS"));

    for (const label of ["Agent OS", "Clients", "Calendar", "Conversations", "Billing"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });
});
