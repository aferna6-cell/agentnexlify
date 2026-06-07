import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
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
      screen.getByText("Loaded business profile (businessName, ownerName, city)"),
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
