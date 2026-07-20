import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  fetchOsRunTrace: vi.fn(),
}));

import { fetchOsRunTrace } from "../../utils/api/os";
import RunTraceDrawer from "./RunTraceDrawer";

function tracePayload(over = {}) {
  return {
    run: {
      id: "r1",
      agent_name: "sales",
      status: "succeeded",
      deliverable_status: "pending_approval",
      thought_process: ["Read the ask", "Drafted the reply"],
      deliverable: { guard_flags: [] },
    },
    routing_decisions: [
      { classifier: "heuristic", chosen_agent: "sales", confidence: 0.92 },
    ],
    model_calls: [
      {
        purpose: "draft",
        model: "claude-sonnet-5",
        input_tokens: 900,
        output_tokens: 220,
        ok: true,
      },
    ],
    action_runs: [{ action_type: "email.send", status: "succeeded" }],
    messages: [],
    ...over,
  };
}

beforeEach(() => {
  fetchOsRunTrace.mockReset();
});

describe("RunTraceDrawer", () => {
  it("renders nothing without a runId", () => {
    const { container } = render(<RunTraceDrawer token="jwt" runId={null} />);
    expect(container.innerHTML).toBe("");
  });

  it("opens and shows the full timeline", async () => {
    fetchOsRunTrace.mockResolvedValue(tracePayload());
    render(<RunTraceDrawer token="jwt" runId="r1" />);
    fireEvent.click(screen.getByText("View run trace"));

    expect(await screen.findByText(/sales — succeeded/)).toBeInTheDocument();
    expect(screen.getByText(/heuristic: chose sales/)).toBeInTheDocument();
    expect(screen.getByText("Read the ask")).toBeInTheDocument();
    expect(screen.getByText(/draft · claude-sonnet-5 · 900 in/)).toBeInTheDocument();
    expect(screen.getByText(/email.send — succeeded/)).toBeInTheDocument();
    expect(fetchOsRunTrace).toHaveBeenCalledWith("jwt", "r1");
  });

  it("surfaces guardrail holds", async () => {
    const payload = tracePayload();
    payload.run.deliverable.guard_flags = ["payment_redirect"];
    fetchOsRunTrace.mockResolvedValue(payload);
    render(<RunTraceDrawer token="jwt" runId="r1" />);
    fireEvent.click(screen.getByText("View run trace"));
    expect(
      await screen.findByText(/Held by outbound guard: payment_redirect/)
    ).toBeInTheDocument();
  });

  it("shows fetch errors", async () => {
    fetchOsRunTrace.mockRejectedValue(new Error("API 404"));
    render(<RunTraceDrawer token="jwt" runId="r1" />);
    fireEvent.click(screen.getByText("View run trace"));
    expect(await screen.findByText("API 404")).toBeInTheDocument();
  });

  it("closes via the close button", async () => {
    fetchOsRunTrace.mockResolvedValue(tracePayload());
    render(<RunTraceDrawer token="jwt" runId="r1" />);
    fireEvent.click(screen.getByText("View run trace"));
    await screen.findByText(/sales — succeeded/);
    fireEvent.click(screen.getByText("Close"));
    expect(screen.queryByText(/sales — succeeded/)).not.toBeInTheDocument();
  });

  it("renders empty-section labels when trace is sparse", async () => {
    fetchOsRunTrace.mockResolvedValue(
      tracePayload({
        routing_decisions: [],
        model_calls: [],
        action_runs: [],
        run: { agent_name: "sales", status: "succeeded", thought_process: [] },
      })
    );
    render(<RunTraceDrawer token="jwt" runId="r1" />);
    fireEvent.click(screen.getByText("View run trace"));
    expect(
      await screen.findByText("No routing decisions recorded")
    ).toBeInTheDocument();
    expect(screen.getByText("No trace steps recorded")).toBeInTheDocument();
    expect(screen.getByText("No model calls recorded")).toBeInTheDocument();
    expect(screen.getByText("No actions fired")).toBeInTheDocument();
  });
});
