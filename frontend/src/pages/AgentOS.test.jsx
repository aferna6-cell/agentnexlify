import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let mockAuth;
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("../utils/api/os", () => ({
  listOsThreads: vi.fn(),
  createOsThread: vi.fn(),
  fetchOsThreadMessages: vi.fn(),
  postOsMessage: vi.fn(),
  fetchOsUsage: vi.fn(),
}));

vi.mock("../components/os/AgentRunFlowchart", () => ({
  default: ({ run }) => <div data-testid="flowchart">{run?.status}</div>,
}));

vi.mock("../components/os/DeliverablePanel", () => ({
  default: ({ run, onClose }) => (
    <div data-testid="panel">
      <span>panel-{run?.id}</span>
      <button onClick={onClose}>close-panel</button>
    </div>
  ),
}));

import {
  listOsThreads,
  createOsThread,
  fetchOsThreadMessages,
  postOsMessage,
  fetchOsUsage,
} from "../utils/api/os";
import AgentOS from "./AgentOS";

const NOW = new Date().toISOString();

beforeEach(() => {
  mockAuth = { token: "jwt" };
  listOsThreads.mockReset().mockResolvedValue([]);
  createOsThread.mockReset();
  fetchOsThreadMessages
    .mockReset()
    .mockResolvedValue({ messages: [], agent_runs: [] });
  postOsMessage.mockReset();
  fetchOsUsage.mockReset().mockResolvedValue({ cap_reached: false });
});

describe("AgentOS shell", () => {
  it("shows the thread loading state before threads arrive", () => {
    let resolve;
    listOsThreads.mockReturnValueOnce(new Promise((r) => (resolve = r)));
    render(<AgentOS />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
    resolve([]);
  });

  it("renders the empty thread rail and empty chat state", async () => {
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText(/No tasks yet/i)).toBeInTheDocument(),
    );
    expect(
      screen.getByText("Hand a task to the orchestrator"),
    ).toBeInTheDocument();
  });

  it("surfaces a load error when the thread fetch fails", async () => {
    listOsThreads.mockReset().mockRejectedValueOnce(new Error("boom"));
    render(<AgentOS />);
    await waitFor(() => expect(screen.getByText("boom")).toBeInTheDocument());
  });

  it("loads threads and renders the active thread's messages", async () => {
    listOsThreads.mockResolvedValueOnce([
      { id: "t1", title: "Task one", created_at: NOW },
    ]);
    fetchOsThreadMessages.mockResolvedValueOnce({
      messages: [{ id: "m1", role: "user", content: "first task" }],
      agent_runs: [],
    });
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText("first task")).toBeInTheDocument(),
    );
    expect(screen.getByText("Task one")).toBeInTheDocument();
  });

  it("shows the cap banner and disables the composer when capped", async () => {
    fetchOsUsage.mockReset().mockResolvedValue({
      cap_reached: true,
      cap: 50,
      agent_runs: 50,
    });
    render(<AgentOS />);
    await waitFor(() =>
      expect(
        screen.getByText(/Monthly agent-run cap reached/i),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByPlaceholderText("Agent-run cap reached for this cycle"),
    ).toBeDisabled();
  });

  it("creates a new thread from the New task button", async () => {
    createOsThread.mockResolvedValueOnce({
      id: "t9",
      title: "New conversation",
      created_at: NOW,
    });
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText(/No tasks yet/i)).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText("New task"));
    await waitFor(() =>
      expect(screen.getByText("New conversation")).toBeInTheDocument(),
    );
    expect(createOsThread).toHaveBeenCalledWith("jwt");
    // The fresh thread becomes active, so the empty-rail state clears.
    expect(screen.queryByText(/No tasks yet/i)).not.toBeInTheDocument();
  });

  it("sends a message and appends the user + assistant turns", async () => {
    listOsThreads.mockResolvedValueOnce([
      { id: "t1", title: "Task one", created_at: NOW },
    ]);
    postOsMessage.mockResolvedValueOnce({
      user_message: { id: "u1", role: "user", content: "do the thing" },
      assistant_message: { id: "a1", role: "assistant", content: "on it" },
      agent_runs: [],
    });
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText("Task one")).toBeInTheDocument(),
    );
    fireEvent.change(
      screen.getByPlaceholderText("Describe a task for the orchestrator..."),
      { target: { value: "do the thing" } },
    );
    fireEvent.click(screen.getByText("Send"));
    await waitFor(() => expect(screen.getByText("on it")).toBeInTheDocument());
    expect(screen.getByText("do the thing")).toBeInTheDocument();
    expect(postOsMessage).toHaveBeenCalledWith("jwt", "t1", "do the thing");
  });

  it("sends on Enter without shift", async () => {
    listOsThreads.mockResolvedValueOnce([
      { id: "t1", title: "Task one", created_at: NOW },
    ]);
    postOsMessage.mockResolvedValueOnce({
      user_message: { id: "u1", role: "user", content: "via enter" },
      assistant_message: { id: "a1", role: "assistant", content: "got it" },
      agent_runs: [],
    });
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText("Task one")).toBeInTheDocument(),
    );
    const composer = screen.getByPlaceholderText(
      "Describe a task for the orchestrator...",
    );
    fireEvent.change(composer, { target: { value: "via enter" } });
    fireEvent.keyDown(composer, { key: "Enter", shiftKey: false });
    await waitFor(() => expect(screen.getByText("got it")).toBeInTheDocument());
  });

  it("shows a cap error when the send is rejected with 429", async () => {
    listOsThreads.mockResolvedValueOnce([
      { id: "t1", title: "Task one", created_at: NOW },
    ]);
    const err = new Error("too many");
    err.status = 429;
    postOsMessage.mockRejectedValueOnce(err);
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText("Task one")).toBeInTheDocument(),
    );
    fireEvent.change(
      screen.getByPlaceholderText("Describe a task for the orchestrator..."),
      { target: { value: "overflow" } },
    );
    fireEvent.click(screen.getByText("Send"));
    await waitFor(() =>
      expect(
        screen.getByText(/Monthly agent-run cap reached for this billing/i),
      ).toBeInTheDocument(),
    );
  });

  it("renders the run flowchart for an assistant message with a run", async () => {
    listOsThreads.mockResolvedValueOnce([
      { id: "t1", title: "Task one", created_at: NOW },
    ]);
    fetchOsThreadMessages.mockResolvedValueOnce({
      messages: [
        {
          id: "m1",
          role: "assistant",
          content: "delegated it",
          agent_run_id: "r1",
        },
      ],
      agent_runs: [{ id: "r1", status: "succeeded" }],
    });
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByTestId("flowchart")).toBeInTheDocument(),
    );
  });

  it("shows a source badge for inbound threads but not owner-typed threads", async () => {
    listOsThreads.mockResolvedValueOnce([
      {
        id: "tw",
        title: "Widget visitor",
        source: "widget",
        created_at: NOW,
      },
      { id: "tc", title: "Owner task", source: "chat", created_at: NOW },
    ]);
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText("Widget visitor")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("thread-source-tw")).toHaveTextContent("Widget");
    expect(screen.queryByTestId("thread-source-tc")).not.toBeInTheDocument();
  });

  it("filters the thread rail by source pill", async () => {
    listOsThreads.mockResolvedValueOnce([
      { id: "tw", title: "Widget chat", source: "widget", created_at: NOW },
      { id: "tc", title: "Owner only", source: "chat", created_at: NOW },
    ]);
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText("Widget chat")).toBeInTheDocument(),
    );
    expect(screen.getByText("Owner only")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Widget" }));
    await waitFor(() =>
      expect(screen.queryByText("Owner only")).not.toBeInTheDocument(),
    );
    expect(screen.getByText("Widget chat")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "All" }));
    await waitFor(() =>
      expect(screen.getByText("Owner only")).toBeInTheDocument(),
    );
  });

  it("shows an empty-filter message when no thread matches", async () => {
    listOsThreads.mockResolvedValueOnce([
      { id: "tc", title: "Owner only", source: "chat", created_at: NOW },
    ]);
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText("Owner only")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Email" }));
    await waitFor(() =>
      expect(
        screen.getByText(/No threads match this source filter/i),
      ).toBeInTheDocument(),
    );
  });

  it("treats threads without a source field as owner-typed", async () => {
    listOsThreads.mockResolvedValueOnce([
      { id: "t1", title: "Legacy thread", created_at: NOW },
    ]);
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText("Legacy thread")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("thread-source-t1")).not.toBeInTheDocument();
  });

  it("opens the deliverable panel from a draft review button", async () => {
    listOsThreads.mockResolvedValueOnce([
      { id: "t1", title: "Task one", created_at: NOW },
    ]);
    fetchOsThreadMessages.mockResolvedValueOnce({
      messages: [
        {
          id: "m1",
          role: "agent",
          content: "draft ready",
          agent_run_id: "r1",
        },
      ],
      agent_runs: [
        {
          id: "r1",
          status: "succeeded",
          deliverable: { title: "D", body: "B" },
        },
      ],
    });
    render(<AgentOS />);
    await waitFor(() =>
      expect(screen.getByText("Review draft")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText("Review draft"));
    expect(screen.getByText("panel-r1")).toBeInTheDocument();
    fireEvent.click(screen.getByText("close-panel"));
    expect(screen.queryByText("panel-r1")).not.toBeInTheDocument();
  });
});
