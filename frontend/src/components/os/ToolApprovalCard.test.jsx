import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  approveOsToolExecution: vi.fn(),
  rejectOsToolExecution: vi.fn(),
}));

import {
  approveOsToolExecution,
  rejectOsToolExecution,
} from "../../utils/api/os";
import ToolApprovalCard from "./ToolApprovalCard";

const TOKEN = "jwt";

function pending(overrides = {}) {
  return {
    id: "exec-1",
    tool_id: "send_email",
    agent_id: "sales",
    risk_level: 2,
    status: "pending_approval",
    input: {
      to: "sarah@example.com",
      subject: "Following up on your brake quote",
      body: "Hi Sarah,\n\nJust following up on the quote.",
    },
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ToolApprovalCard", () => {
  it("shows the owner exactly what will be sent, and to whom, before approving", () => {
    render(<ToolApprovalCard execution={pending()} token={TOKEN} />);

    expect(screen.getByTestId("tool-approval-recipient")).toHaveTextContent(
      "sarah@example.com",
    );
    expect(screen.getByTestId("tool-approval-subject")).toHaveTextContent(
      "Following up on your brake quote",
    );
    expect(screen.getByTestId("tool-approval-body")).toHaveTextContent(
      "Just following up on the quote.",
    );
    expect(screen.getByText(/sends outside your business/i)).toBeInTheDocument();
    expect(screen.getByText(/requested by your sales agent/i)).toBeInTheDocument();
  });

  it("sends only when the owner approves, and reports the result", async () => {
    approveOsToolExecution.mockResolvedValue({
      execution: { ...pending(), status: "succeeded", verification_state: "passed" },
    });
    const onUpdated = vi.fn();
    render(<ToolApprovalCard execution={pending()} token={TOKEN} onUpdated={onUpdated} />);

    fireEvent.click(screen.getByRole("button", { name: /approve and send/i }));

    await waitFor(() => expect(onUpdated).toHaveBeenCalled());
    expect(onUpdated.mock.calls[0][0].status).toBe("succeeded");
  });

  it("does not fire a second send while the first is in flight", async () => {
    let resolve;
    approveOsToolExecution.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );
    render(<ToolApprovalCard execution={pending()} token={TOKEN} />);

    const approve = screen.getByRole("button", { name: /approve and send/i });
    fireEvent.click(approve);
    fireEvent.click(approve);
    fireEvent.click(approve);

    expect(approve).toBeDisabled();
    resolve({ execution: { ...pending(), status: "succeeded" } });
    await waitFor(() =>
      expect(approveOsToolExecution.mock.calls.length).toBe(1),
    );
  });

  it("rejects without sending", async () => {
    rejectOsToolExecution.mockResolvedValue({ ...pending(), status: "denied" });
    const onUpdated = vi.fn();
    render(<ToolApprovalCard execution={pending()} token={TOKEN} onUpdated={onUpdated} />);

    fireEvent.click(screen.getByRole("button", { name: /reject/i }));

    await waitFor(() => expect(onUpdated).toHaveBeenCalled());
    expect(approveOsToolExecution).not.toHaveBeenCalled();
    expect(onUpdated.mock.calls[0][0].status).toBe("denied");
  });

  it("says nothing was sent when the approval call fails", async () => {
    approveOsToolExecution.mockRejectedValue(new Error("network down"));
    render(<ToolApprovalCard execution={pending()} token={TOKEN} />);

    fireEvent.click(screen.getByRole("button", { name: /approve and send/i }));

    await waitFor(() =>
      expect(screen.getByText(/network down/i)).toBeInTheDocument(),
    );
  });

  it("reads a ran-but-unverified action as unconfirmed, not as sent", () => {
    render(
      <ToolApprovalCard
        execution={pending({
          status: "verification_failed",
          verification_state: "failed",
          verification_detail:
            "Gmail accepted the send but message gmail-msg-1 could not be read back, so delivery is unconfirmed",
        })}
        token={TOKEN}
      />,
    );

    expect(screen.getByText(/ran, but unconfirmed/i)).toBeInTheDocument();
    expect(screen.getByText(/Not confirmed:/)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /approve and send/i }),
    ).not.toBeInTheDocument();
  });

  it("offers no approval button once the action is already decided", () => {
    render(<ToolApprovalCard execution={pending({ status: "denied" })} token={TOKEN} />);

    expect(screen.getByText(/rejected - never sent/i)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
