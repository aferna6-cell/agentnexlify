import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  runOsResearch: vi.fn(),
  createProjectFromResearch: vi.fn(),
}));

import {
  createProjectFromResearch,
  runOsResearch,
} from "../../utils/api/os";
import ResearchCard from "./ResearchCard";

const BRIEF_RUN = {
  id: "r1",
  deliverable: {
    title: "Research brief: pricing strategy",
    body: "Key findings:\n- Regulars respond to bundles.",
  },
};

beforeEach(() => {
  runOsResearch.mockReset();
  createProjectFromResearch.mockReset();
});

function typeTopic(value) {
  fireEvent.change(
    screen.getByPlaceholderText(/What do our regulars ask/),
    { target: { value } },
  );
}

describe("ResearchCard", () => {
  it("runs research and renders the brief", async () => {
    runOsResearch.mockResolvedValue({ run: BRIEF_RUN });
    render(<ResearchCard token="jwt" />);
    typeTopic("How do regulars respond to pricing?");
    fireEvent.click(screen.getByText("Research"));
    expect(
      await screen.findByText("Research brief: pricing strategy"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Regulars respond to bundles/)).toBeInTheDocument();
    expect(screen.getByText(/Pending approvals/)).toBeInTheDocument();
    expect(runOsResearch).toHaveBeenCalledWith(
      "jwt",
      "How do regulars respond to pricing?",
      [],
    );
  });

  it("passes comma-separated web page URLs, capped at three", async () => {
    runOsResearch.mockResolvedValue({ run: BRIEF_RUN });
    render(<ResearchCard token="jwt" />);
    typeTopic("How does our pricing compare to competitors?");
    fireEvent.change(screen.getByPlaceholderText(/web pages to include/), {
      target: {
        value: "https://a.com, b.com/pricing , https://c.com, https://d.com",
      },
    });
    fireEvent.click(screen.getByText("Research"));
    expect(
      await screen.findByText("Research brief: pricing strategy"),
    ).toBeInTheDocument();
    expect(runOsResearch).toHaveBeenCalledWith(
      "jwt",
      "How does our pricing compare to competitors?",
      ["https://a.com", "b.com/pricing", "https://c.com"],
    );
  });

  it("rejects a too-short topic without calling the API", async () => {
    render(<ResearchCard token="jwt" />);
    typeTopic("short");
    fireEvent.click(screen.getByText("Research"));
    expect(
      await screen.findByText(/at least 10 characters/),
    ).toBeInTheDocument();
    expect(runOsResearch).not.toHaveBeenCalled();
  });

  it("shows the API error message on failure", async () => {
    runOsResearch.mockRejectedValue(
      new Error("No owned sources to research from yet"),
    );
    render(<ResearchCard token="jwt" />);
    typeTopic("What should we do about churned regulars?");
    fireEvent.keyDown(
      screen.getByPlaceholderText(/What do our regulars ask/),
      { key: "Enter" },
    );
    expect(
      await screen.findByText(/No owned sources to research from yet/),
    ).toBeInTheDocument();
  });

  it("acts on the brief by drafting a project", async () => {
    runOsResearch.mockResolvedValue({ run: BRIEF_RUN });
    createProjectFromResearch.mockResolvedValue({
      project: { id: "p9", title: "Bundle push", status: "draft" },
      steps: [],
    });
    render(<ResearchCard token="jwt" />);
    typeTopic("How do regulars respond to pricing?");
    fireEvent.click(screen.getByText("Research"));
    fireEvent.click(await screen.findByText("Act on this brief"));
    expect(
      await screen.findByText(/Project drafted: "Bundle push"/),
    ).toBeInTheDocument();
    expect(createProjectFromResearch).toHaveBeenCalledWith("jwt", "r1");
  });

  it("surfaces a planner snag without pretending success", async () => {
    runOsResearch.mockResolvedValue({ run: BRIEF_RUN });
    createProjectFromResearch.mockResolvedValue({
      project: { id: "p9", status: "draft", error: "planner failed: 400" },
      steps: [],
    });
    render(<ResearchCard token="jwt" />);
    typeTopic("How do regulars respond to pricing?");
    fireEvent.click(screen.getByText("Research"));
    fireEvent.click(await screen.findByText("Act on this brief"));
    expect(
      await screen.findByText(/planning hit a snag/),
    ).toBeInTheDocument();
  });

  it("shows the handoff error when project creation fails", async () => {
    runOsResearch.mockResolvedValue({ run: BRIEF_RUN });
    createProjectFromResearch.mockRejectedValue(
      new Error("active project limit reached"),
    );
    render(<ResearchCard token="jwt" />);
    typeTopic("How do regulars respond to pricing?");
    fireEvent.click(screen.getByText("Research"));
    fireEvent.click(await screen.findByText("Act on this brief"));
    expect(
      await screen.findByText(/active project limit reached/),
    ).toBeInTheDocument();
  });
});
