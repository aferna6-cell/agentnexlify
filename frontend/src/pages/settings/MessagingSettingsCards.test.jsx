import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { AgentOSAutoSendCard } from "./MessagingSettingsCards";

// The per-agent auto-send toggle writes os_auto_send_rules keyed by the agent
// name. The backend (resolve_deliverable_status) looks those keys up against
// the engine's persisted department ids. The pre-fix UI used retired v1 skill
// ids (customer_question/booking/lead_nurture/campaign/generalist) that never
// matched a persisted agent_name, so the toggle silently did nothing. These
// tests lock the keys to real department ids.

function renderCard(overrides = {}) {
  const setForm = vi.fn();
  const props = {
    form: { os_auto_send_enabled: false, os_auto_send_rules: {}, ...overrides },
    setForm,
    setSaved: vi.fn(),
    handleSave: vi.fn(),
    saving: false,
    saved: false,
  };
  render(<AgentOSAutoSendCard {...props} />);
  return { setForm };
}

describe("AgentOSAutoSendCard per-agent toggles", () => {
  it("labels the real, auto-sendable departments and drops retired v1 ids", () => {
    renderCard();
    expect(screen.getByText("Sales replies & lead follow-ups")).toBeInTheDocument();
    expect(screen.getByText("Marketing & campaign drafts")).toBeInTheDocument();
    expect(screen.getByText("Operations & scheduling")).toBeInTheDocument();
    // retired v1 labels must be gone
    expect(screen.queryByText("Customer questions (FAQ answers)")).toBeNull();
    expect(screen.queryByText("General assistant")).toBeNull();
    expect(screen.queryByText("Campaigns")).toBeNull();
  });

  it("writes os_auto_send_rules keyed by the department id (sales), not a v1 id", () => {
    const { setForm } = renderCard();
    // The three per-agent selects render in AUTO_SEND_AGENTS order: sales, marketing, operations.
    const selects = screen.getAllByRole("combobox");
    expect(selects).toHaveLength(3);

    fireEvent.change(selects[0], { target: { value: "auto" } });

    expect(setForm).toHaveBeenCalledTimes(1);
    const updater = setForm.mock.calls[0][0];
    const next = updater({ os_auto_send_rules: {} });
    expect(next.os_auto_send_rules).toEqual({ sales: true });
    // proves the old broken key is NOT what gets written
    expect(next.os_auto_send_rules.customer_question).toBeUndefined();
  });

  it("'Always ask me' writes false for the department id", () => {
    const { setForm } = renderCard();
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[2], { target: { value: "approve" } }); // operations

    const updater = setForm.mock.calls[0][0];
    const next = updater({ os_auto_send_rules: {} });
    expect(next.os_auto_send_rules).toEqual({ operations: false });
  });

  it("'Follow global' removes the per-agent rule key", () => {
    const { setForm } = renderCard({ os_auto_send_rules: { marketing: true } });
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[1], { target: { value: "default" } }); // marketing

    const updater = setForm.mock.calls[0][0];
    const next = updater({ os_auto_send_rules: { marketing: true } });
    expect(next.os_auto_send_rules).toEqual({});
  });
});
