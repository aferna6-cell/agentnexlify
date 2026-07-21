import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  askBusinessData: vi.fn(),
  fetchAskDataSupported: vi.fn(),
}));

import { askBusinessData, fetchAskDataSupported } from "../../utils/api/os";
import AskDataCard from "./AskDataCard";

beforeEach(() => {
  askBusinessData.mockReset();
  fetchAskDataSupported.mockReset();
  fetchAskDataSupported.mockResolvedValue({
    supported_questions: ["How many leads did I get this week?"],
  });
});

describe("AskDataCard", () => {
  it("shows example chips from the supported list", async () => {
    render(<AskDataCard token="jwt" />);
    expect(
      await screen.findByText("How many leads did I get this week?")
    ).toBeInTheDocument();
  });

  it("asks a typed question on Enter and renders the answer", async () => {
    askBusinessData.mockResolvedValue({
      matched: true,
      answer: "You got 4 new lead(s) in the last week.",
    });
    render(<AskDataCard token="jwt" />);
    const input = screen.getByPlaceholderText(/How many leads/);
    fireEvent.change(input, { target: { value: "leads this week?" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(
      await screen.findByText(/You got 4 new lead/)
    ).toBeInTheDocument();
    expect(askBusinessData).toHaveBeenCalledWith("jwt", "leads this week?");
  });

  it("asks via an example chip click", async () => {
    askBusinessData.mockResolvedValue({ answer: "12 conversations." });
    render(<AskDataCard token="jwt" />);
    fireEvent.click(
      await screen.findByText("How many leads did I get this week?")
    );
    expect(await screen.findByText("12 conversations.")).toBeInTheDocument();
  });

  it("renders the error message when the ask fails", async () => {
    askBusinessData.mockRejectedValue(new Error("nope"));
    render(<AskDataCard token="jwt" />);
    const input = screen.getByPlaceholderText(/How many leads/);
    fireEvent.change(input, { target: { value: "anything at all" } });
    fireEvent.click(screen.getByText("Ask"));
    expect(await screen.findByText("nope")).toBeInTheDocument();
  });
});
