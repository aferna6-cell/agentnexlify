import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import AgentRunFlowchart from "./AgentRunFlowchart";

describe("AgentRunFlowchart", () => {
  it("renders nothing without a run", () => {
    const { container } = render(<AgentRunFlowchart run={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the agent name and status pill", () => {
    render(
      <AgentRunFlowchart
        run={{ agent_name: "Email drafter", status: "running" }}
      />,
    );
    expect(screen.getByText("Email drafter")).toBeInTheDocument();
    expect(screen.getByText("Running")).toBeInTheDocument();
  });

  it("falls back to a default agent name and queued status", () => {
    render(<AgentRunFlowchart run={{}} />);
    expect(screen.getByText("Worker agent")).toBeInTheDocument();
    expect(screen.getByText("Queued")).toBeInTheDocument();
  });

  it("shows a startup message when in flight with no steps", () => {
    render(
      <AgentRunFlowchart run={{ status: "queued", thought_process: [] }} />,
    );
    expect(screen.getByText("Agent is starting up...")).toBeInTheDocument();
  });

  it("does not show the startup message once a run has completed", () => {
    render(<AgentRunFlowchart run={{ status: "succeeded" }} />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(
      screen.queryByText("Agent is starting up..."),
    ).not.toBeInTheDocument();
  });

  it("renders the thought-process timeline with labels and details", () => {
    render(
      <AgentRunFlowchart
        run={{
          status: "running",
          thought_process: [
            {
              step: 1,
              label: "Read the brief",
              status: "done",
              detail: "Parsed the request",
              at: "2026-05-21T10:00:00Z",
            },
            { step: 2, status: "running", detail: "Drafting" },
          ],
        }}
      />,
    );
    expect(screen.getByText("Read the brief")).toBeInTheDocument();
    expect(screen.getByText("Parsed the request")).toBeInTheDocument();
    // step without a label falls back to its index position
    expect(screen.getByText("Step 2")).toBeInTheDocument();
    expect(screen.getByText("Drafting")).toBeInTheDocument();
  });

  it("renders the v2 agent-service trace shape (description/ordinal/status)", () => {
    render(
      <AgentRunFlowchart
        run={{
          agent_name: "operations",
          status: "succeeded",
          thought_process: [
            {
              runId: "r1",
              ordinal: 0,
              step: "route",
              status: "work",
              description: "Routing to the Operations agent",
            },
            {
              runId: "r1",
              ordinal: 2,
              step: "load_business_profile",
              status: "completed",
              description:
                "Loaded business profile (businessName, ownerName, city)",
              dataSnapshot: ["businessName", "ownerName", "city"],
            },
          ],
        }}
      />,
    );
    expect(
      screen.getByText("Routing to the Operations agent"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Loaded business profile (businessName, ownerName, city)",
      ),
    ).toBeInTheDocument();
  });

  it("renders the routing chip when routing data is present", () => {
    render(
      <AgentRunFlowchart
        run={{
          agent_name: "operations",
          status: "succeeded",
          routing: {
            chosen_agent: "operations",
            confidence: 0.92,
            model: "claude-haiku-4-5-20251001",
          },
          thought_process: [],
        }}
      />,
    );
    expect(
      screen.queryByText(
        "Routed to operations · 92% · claude-haiku-4-5-20251001",
      ),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Details" }));
    expect(
      screen.getByText(
        "Routed to operations · 92% · claude-haiku-4-5-20251001",
      ),
    ).toBeInTheDocument();
  });

  it("hides mode and skill names until Details is opened", () => {
    render(
      <AgentRunFlowchart
        run={{
          agent_name: "Operations",
          status: "succeeded",
          thought_process: [
            {
              step: "select_skill",
              description: "Operations → Booking skill",
              status: "work",
            },
            {
              step: "compose_message",
              description: "mode=propose, slot=none provided",
              status: "work",
            },
            {
              step: "load_business_profile",
              description: "Loaded business profile (businessName)",
              status: "completed",
            },
          ],
        }}
      />,
    );
    expect(
      screen.getByText("Loaded business profile (businessName)"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Operations → Booking skill"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("mode=propose, slot=none provided"),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Details" }));
    expect(screen.getByText("Operations → Booking skill")).toBeInTheDocument();
    expect(
      screen.getByText("mode=propose, slot=none provided"),
    ).toBeInTheDocument();
  });

  it("renders the error block on a failed run", () => {
    render(
      <AgentRunFlowchart
        run={{ status: "failed", error_detail: "Worker crashed" }}
      />,
    );
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Worker crashed")).toBeInTheDocument();
  });

  it("ignores an invalid step timestamp without crashing", () => {
    render(
      <AgentRunFlowchart
        run={{
          status: "running",
          thought_process: [{ step: 1, label: "Bad time", at: "not-a-date" }],
        }}
      />,
    );
    expect(screen.getByText("Bad time")).toBeInTheDocument();
  });
});
