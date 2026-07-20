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
  it("renders all four cards with fetched data", async () => {
    render(<AgentControlsPage />);
    expect(await screen.findByText("Agent Controls")).toBeInTheDocument();
    expect(await screen.findByText("Department instructions")).toBeInTheDocument();
    expect(await screen.findByDisplayValue("Mention referrals")).toBeInTheDocument();
    expect(await screen.findByText("Golden questions")).toBeInTheDocument();
    expect(await screen.findByText("What are your hours?")).toBeInTheDocument();
    expect(await screen.findByText("Usage this cycle")).toBeInTheDocument();
    expect(await screen.findByText("1,200")).toBeInTheDocument();
    expect(screen.getByText("Activity export")).toBeInTheDocument();
    expect(screen.getByText("Download CSV")).toBeInTheDocument();
  });

  it("shows last eval run summary", async () => {
    render(<AgentControlsPage />);
    expect(await screen.findByText(/Last run: 1\/1 passing/)).toBeInTheDocument();
  });

  it("saves an edited instruction", async () => {
    render(<AgentControlsPage />);
    const textarea = await screen.findByDisplayValue("Mention referrals");
    fireEvent.change(textarea, { target: { value: "Push gift cards" } });
    const saveButtons = screen.getAllByText("Save");
    fireEvent.click(saveButtons[0]);
    await waitFor(() =>
      expect(putOsInstruction).toHaveBeenCalledWith("jwt", "sales", "Push gift cards")
    );
  });

  it("adds a golden question with comma-split phrases", async () => {
    render(<AgentControlsPage />);
    await screen.findByText("Golden questions");
    fireEvent.change(
      screen.getByPlaceholderText(/Customer question/),
      { target: { value: "Do you take walk-ins?" } }
    );
    fireEvent.change(
      screen.getByPlaceholderText(/Expected phrases/),
      { target: { value: "walk-ins, welcome" } }
    );
    fireEvent.click(screen.getByText("Add question"));
    await waitFor(() =>
      expect(createEvalQuestion).toHaveBeenCalledWith("jwt", {
        question: "Do you take walk-ins?",
        expected_phrases: ["walk-ins", "welcome"],
      })
    );
  });

  it("runs checks on demand", async () => {
    render(<AgentControlsPage />);
    fireEvent.click(await screen.findByText("Run checks now"));
    await waitFor(() => expect(runEvals).toHaveBeenCalledWith("jwt"));
  });

  it("removes a question", async () => {
    render(<AgentControlsPage />);
    fireEvent.click(await screen.findByText("Remove"));
    await waitFor(() =>
      expect(deleteEvalQuestion).toHaveBeenCalledWith("jwt", "q1")
    );
  });

  it("shows empty usage state", async () => {
    fetchOsUsageBreakdown.mockResolvedValue({
      cycle_start: "2026-07-01",
      departments: [],
    });
    render(<AgentControlsPage />);
    expect(
      await screen.findByText(/No agent activity yet this cycle/)
    ).toBeInTheDocument();
  });

  it("asks for sign-in without a token", () => {
    mockAuth = { user: null, token: null };
    render(<AgentControlsPage />);
    expect(screen.getByText(/Sign in to manage agent controls/)).toBeInTheDocument();
  });
});
