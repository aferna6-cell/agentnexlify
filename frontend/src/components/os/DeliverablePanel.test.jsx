import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  editOsDeliverable: vi.fn(),
  approveOsDeliverable: vi.fn(),
  rejectOsDeliverable: vi.fn(),
  reportOsRunBug: vi.fn(),
}));

import {
  editOsDeliverable,
  approveOsDeliverable,
  rejectOsDeliverable,
  reportOsRunBug,
} from "../../utils/api/os";
import DeliverablePanel from "./DeliverablePanel";

const TOKEN = "jwt";

function pendingRun(overrides = {}) {
  return {
    id: "r1",
    deliverable_status: "pending_approval",
    deliverable: { title: "Draft title", body: "Draft body" },
    ...overrides,
  };
}

beforeEach(() => {
  editOsDeliverable.mockReset();
  approveOsDeliverable.mockReset();
  rejectOsDeliverable.mockReset();
  reportOsRunBug.mockReset();
});

describe("DeliverablePanel", () => {
  it("renders nothing without a run", () => {
    const { container } = render(
      <DeliverablePanel run={null} token={TOKEN} onClose={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the run has no deliverable", () => {
    const { container } = render(
      <DeliverablePanel
        run={{ id: "r1", deliverable: null }}
        token={TOKEN}
        onClose={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows editable title and body for a pending deliverable", () => {
    render(
      <DeliverablePanel run={pendingRun()} token={TOKEN} onClose={vi.fn()} />,
    );
    expect(screen.getByDisplayValue("Draft title")).not.toBeDisabled();
    expect(screen.getByDisplayValue("Draft body")).not.toBeDisabled();
    expect(screen.getByText("Pending approval")).toBeInTheDocument();
  });

  it("fires onClose when the close button is clicked", () => {
    const onClose = vi.fn();
    render(
      <DeliverablePanel run={pendingRun()} token={TOKEN} onClose={onClose} />,
    );
    fireEvent.click(screen.getByLabelText("Close draft panel"));
    expect(onClose.mock.calls.length).toBe(1);
  });

  it("keeps the save button disabled until the draft is edited", () => {
    render(
      <DeliverablePanel run={pendingRun()} token={TOKEN} onClose={vi.fn()} />,
    );
    const save = screen.getByText("Save edits");
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByDisplayValue("Draft title"), {
      target: { value: "Edited title" },
    });
    expect(save).not.toBeDisabled();
  });

  it("saves edits and reports the updated run", async () => {
    const updated = pendingRun({ deliverable: { title: "Edited", body: "B" } });
    editOsDeliverable.mockResolvedValueOnce(updated);
    const onUpdated = vi.fn();
    render(
      <DeliverablePanel
        run={pendingRun()}
        token={TOKEN}
        onClose={vi.fn()}
        onUpdated={onUpdated}
      />,
    );
    fireEvent.change(screen.getByDisplayValue("Draft title"), {
      target: { value: "Edited title" },
    });
    fireEvent.click(screen.getByText("Save edits"));
    await waitFor(() => expect(onUpdated).toHaveBeenCalledWith(updated));
    expect(editOsDeliverable).toHaveBeenCalledWith(TOKEN, "r1", {
      title: "Edited title",
      body: "Draft body",
    });
    // Parent receives the run the server returned, not the stale prop.
    expect(onUpdated.mock.calls[0][0]).toEqual(updated);
  });

  it("approves the deliverable", async () => {
    const updated = pendingRun({ deliverable_status: "approved" });
    approveOsDeliverable.mockResolvedValueOnce(updated);
    const onUpdated = vi.fn();
    render(
      <DeliverablePanel
        run={pendingRun()}
        token={TOKEN}
        onClose={vi.fn()}
        onUpdated={onUpdated}
      />,
    );
    fireEvent.click(screen.getByText("Approve"));
    await waitFor(() => expect(onUpdated).toHaveBeenCalledWith(updated));
    expect(approveOsDeliverable).toHaveBeenCalledWith(TOKEN, "r1");
    // The run handed back to the parent carries the approved status.
    expect(onUpdated.mock.calls[0][0].deliverable_status).toBe("approved");
  });

  it("rejects the deliverable", async () => {
    rejectOsDeliverable.mockResolvedValueOnce(
      pendingRun({ deliverable_status: "rejected" }),
    );
    render(
      <DeliverablePanel run={pendingRun()} token={TOKEN} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByText("Reject"));
    await waitFor(() =>
      expect(rejectOsDeliverable).toHaveBeenCalledWith(TOKEN, "r1"),
    );
  });

  it("surfaces an error when an action fails", async () => {
    approveOsDeliverable.mockRejectedValueOnce(new Error("server down"));
    render(
      <DeliverablePanel run={pendingRun()} token={TOKEN} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByText("Approve"));
    await waitFor(() =>
      expect(screen.getByText("server down")).toBeInTheDocument(),
    );
  });

  it("reports a bug and locks the report button", async () => {
    reportOsRunBug.mockResolvedValueOnce(pendingRun());
    render(
      <DeliverablePanel run={pendingRun()} token={TOKEN} onClose={vi.fn()} />,
    );
    fireEvent.click(screen.getByText("Report a problem with this run"));
    await waitFor(() =>
      expect(screen.getByText("Bug reported - thanks")).toBeInTheDocument(),
    );
    expect(reportOsRunBug).toHaveBeenCalledWith(TOKEN, "r1");
    // Button is locked after a report so it can't be filed twice.
    expect(screen.getByText("Bug reported - thanks")).toBeDisabled();
  });

  it("is read-only after a decision", () => {
    render(
      <DeliverablePanel
        run={pendingRun({ deliverable_status: "approved" })}
        token={TOKEN}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByDisplayValue("Draft title")).toBeDisabled();
    expect(screen.queryByText("Approve")).not.toBeInTheDocument();
    expect(screen.getByText(/This draft was approved\./i)).toBeInTheDocument();
  });

  it("shows the bug button already locked when bug_reported_at is set", () => {
    render(
      <DeliverablePanel
        run={pendingRun({ bug_reported_at: "2026-05-21T00:00:00Z" })}
        token={TOKEN}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("Bug reported - thanks")).toBeDisabled();
  });
});
