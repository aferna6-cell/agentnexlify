import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let mockAuth;
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("../utils/api/os", () => ({
  fetchOsInstructions: vi.fn(),
  fetchOsUsageBreakdown: vi.fn(),
  putOsInstruction: vi.fn(),
  // New Agent Controls cards (ask-data, projects, scheduled tasks)
  fetchAskDataSupported: vi.fn(() =>
    Promise.resolve({ supported_questions: [] }),
  ),
  askBusinessData: vi.fn(() => Promise.resolve({ answer: "" })),
  listOsProjects: vi.fn(() => Promise.resolve({ projects: [] })),
  createOsProject: vi.fn(),
  fetchOsProject: vi.fn(),
  approveOsProject: vi.fn(),
  cancelOsProject: vi.fn(),
  listOsTasks: vi.fn(() => Promise.resolve({ tasks: [], departments: [] })),
  fetchOsTaskSuggestions: vi.fn(() => Promise.resolve({ suggestions: [] })),
  createOsTask: vi.fn(),
  updateOsTask: vi.fn(),
  deleteOsTask: vi.fn(),
  // Deep research card
  runOsResearch: vi.fn(),
  createProjectFromResearch: vi.fn(),
}));

vi.mock("../utils/api/kb-evals", () => ({
  listEvalQuestions: vi.fn(),
  createEvalQuestion: vi.fn(),
  deleteEvalQuestion: vi.fn(),
  runEvals: vi.fn(),
  fetchLatestEvalRun: vi.fn(),
}));

import {
  fetchOsInstructions,
  fetchOsUsageBreakdown,
  putOsInstruction,
} from "../utils/api/os";
import {
  createEvalQuestion,
  deleteEvalQuestion,
  fetchLatestEvalRun,
  listEvalQuestions,
  runEvals,
} from "../utils/api/kb-evals";
import AgentControlsPage from "./AgentControlsPage";

beforeEach(() => {
  mockAuth = { user: { tenantId: "t1" }, token: "jwt" };
  fetchOsInstructions.mockReset().mockResolvedValue({
    departments: ["sales", "marketing"],
    instructions: { sales: "Mention referrals" },
    max_length: 2000,
  });
  fetchOsUsageBreakdown.mockReset().mockResolvedValue({
    cycle_start: "2026-07-01",
    departments: [
      { department: "sales", runs: 3, input_tokens: 1200, output_tokens: 400 },
    ],
  });
  listEvalQuestions.mockReset().mockResolvedValue({
    questions: [
      {
        id: "q1",
        question: "What are your hours?",
        expected_phrases: ["8am-5pm"],
      },
    ],
  });
  fetchLatestEvalRun.mockReset().mockResolvedValue({
    total: 1,
    passed: 1,
    failed: 0,
    regressions: 0,
  });
  createEvalQuestion.mockReset().mockResolvedValue({});
  deleteEvalQuestion.mockReset().mockResolvedValue({ deleted: true });
  runEvals.mockReset().mockResolvedValue({ total: 1, passed: 1 });
  putOsInstruction.mockReset().mockResolvedValue({
    instructions: { sales: "Updated" },
  });
});

describe("AgentControlsPage", () => {
  it("splits tasks, instructions, and usage into tabs", async () => {
    render(<AgentControlsPage />);
    expect(await screen.findByText("Agent Controls")).toBeInTheDocument();
    expect(screen.getByText("Recurring tasks")).toBeInTheDocument();
    expect(
      screen.queryByText("Department instructions"),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Instructions" }));
    expect(
      await screen.findByText("Department instructions"),
    ).toBeInTheDocument();
    expect(
      await screen.findByDisplayValue("Mention referrals"),
    ).toBeInTheDocument();
    expect(screen.getByText("Answer checks")).toBeInTheDocument();
    expect(screen.getByText("What are your hours?")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Save" })).toHaveLength(1);

    fireEvent.click(screen.getByRole("tab", { name: "Usage" }));
    expect(await screen.findByText("Usage this cycle")).toBeInTheDocument();
    expect(await screen.findByText("1,200")).toBeInTheDocument();
    expect(screen.getByText("Activity export")).toBeInTheDocument();
    expect(screen.getByText("Download CSV")).toBeInTheDocument();
  });

  it("shows last eval run summary", async () => {
    render(<AgentControlsPage />);
    fireEvent.click(screen.getByRole("tab", { name: "Instructions" }));
    expect(
      await screen.findByText(/Last run: 1\/1 passing/),
    ).toBeInTheDocument();
  });

  it("saves an edited instruction", async () => {
    render(<AgentControlsPage />);
    fireEvent.click(screen.getByRole("tab", { name: "Instructions" }));
    const textarea = await screen.findByDisplayValue("Mention referrals");
    fireEvent.change(textarea, { target: { value: "Push gift cards" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(putOsInstruction).toHaveBeenCalledWith(
        "jwt",
        "sales",
        "Push gift cards",
      ),
    );
  });

  it("adds an answer check with comma-split phrases", async () => {
    render(<AgentControlsPage />);
    fireEvent.click(screen.getByRole("tab", { name: "Instructions" }));
    await screen.findByText("Answer checks");
    fireEvent.change(screen.getByPlaceholderText(/Customer question/), {
      target: { value: "Do you take walk-ins?" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Expected phrases/), {
      target: { value: "walk-ins, welcome" },
    });
    fireEvent.click(screen.getByText("Add question"));
    await waitFor(() =>
      expect(createEvalQuestion).toHaveBeenCalledWith("jwt", {
        question: "Do you take walk-ins?",
        expected_phrases: ["walk-ins", "welcome"],
      }),
    );
  });

  it("runs checks on demand", async () => {
    render(<AgentControlsPage />);
    fireEvent.click(screen.getByRole("tab", { name: "Instructions" }));
    fireEvent.click(await screen.findByText("Run checks now"));
    await waitFor(() => expect(runEvals).toHaveBeenCalledWith("jwt"));
  });

  it("removes a question", async () => {
    render(<AgentControlsPage />);
    fireEvent.click(screen.getByRole("tab", { name: "Instructions" }));
    fireEvent.click(await screen.findByText("Remove"));
    await waitFor(() =>
      expect(deleteEvalQuestion).toHaveBeenCalledWith("jwt", "q1"),
    );
  });

  it("shows empty usage state", async () => {
    fetchOsUsageBreakdown.mockResolvedValue({
      cycle_start: "2026-07-01",
      departments: [],
    });
    render(<AgentControlsPage />);
    fireEvent.click(screen.getByRole("tab", { name: "Usage" }));
    expect(
      await screen.findByText(/No agent activity yet this cycle/),
    ).toBeInTheDocument();
  });

  it("asks for sign-in without a token", () => {
    mockAuth = { user: null, token: null };
    render(<AgentControlsPage />);
    expect(
      screen.getByText(/Sign in to manage agent controls/),
    ).toBeInTheDocument();
  });
});
