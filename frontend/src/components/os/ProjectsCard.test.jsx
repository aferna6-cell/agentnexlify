import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  listOsProjects: vi.fn(),
  createOsProject: vi.fn(),
  fetchOsProject: vi.fn(),
  approveOsProject: vi.fn(),
  cancelOsProject: vi.fn(),
}));

import {
  approveOsProject,
  cancelOsProject,
  createOsProject,
  fetchOsProject,
  listOsProjects,
} from "../../utils/api/os";
import ProjectsCard from "./ProjectsCard";

const DRAFT = { id: "p1", title: "Spring promo launch", status: "draft" };

beforeEach(() => {
  listOsProjects.mockReset();
  createOsProject.mockReset();
  fetchOsProject.mockReset();
  approveOsProject.mockReset();
  cancelOsProject.mockReset();
  listOsProjects.mockResolvedValue({ projects: [DRAFT] });
});

describe("ProjectsCard", () => {
  it("hides itself entirely when the feature flag is off (list 404s)", async () => {
    listOsProjects.mockRejectedValue(new Error("Projects not enabled"));
    const { container } = render(<ProjectsCard token="jwt" />);
    await waitFor(() => expect(listOsProjects).toHaveBeenCalled());
    expect(container.innerHTML).toBe("");
  });

  it("lists projects with status and an approve button for drafts", async () => {
    render(<ProjectsCard token="jwt" />);
    expect(await screen.findByText("Spring promo launch")).toBeInTheDocument();
    expect(screen.getByText("Approve plan")).toBeInTheDocument();
  });

  it("plans a new project from the big ask", async () => {
    createOsProject.mockResolvedValue({});
    render(<ProjectsCard token="jwt" />);
    await screen.findByText("Spring promo launch");
    fireEvent.change(
      screen.getByPlaceholderText(/What should the team accomplish/),
      { target: { value: "Launch a fall promotion for detailing" } }
    );
    fireEvent.click(screen.getByText("Plan project"));
    await waitFor(() =>
      expect(createOsProject).toHaveBeenCalledWith(
        "jwt",
        "Launch a fall promotion for detailing"
      )
    );
  });

  it("approves a draft plan", async () => {
    approveOsProject.mockResolvedValue({});
    render(<ProjectsCard token="jwt" />);
    await screen.findByText("Spring promo launch");
    fireEvent.click(screen.getByText("Approve plan"));
    await waitFor(() =>
      expect(approveOsProject).toHaveBeenCalledWith("jwt", "p1")
    );
  });

  it("cancels an active project", async () => {
    cancelOsProject.mockResolvedValue({});
    render(<ProjectsCard token="jwt" />);
    await screen.findByText("Spring promo launch");
    fireEvent.click(screen.getByText("Cancel"));
    await waitFor(() =>
      expect(cancelOsProject).toHaveBeenCalledWith("jwt", "p1")
    );
  });

  it("expands steps with per-step status pills", async () => {
    fetchOsProject.mockResolvedValue({
      project: DRAFT,
      steps: [
        {
          id: "s1",
          position: 1,
          department: "marketing",
          objective: "Draft the promo email",
          status: "awaiting_approval",
        },
      ],
    });
    render(<ProjectsCard token="jwt" />);
    await screen.findByText("Spring promo launch");
    fireEvent.click(screen.getByText("Steps"));
    expect(await screen.findByText("Draft the promo email")).toBeInTheDocument();
    expect(screen.getByText("awaiting approval")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Hide steps"));
  });

  it("shows the planner error on a failed create", async () => {
    createOsProject.mockRejectedValue(new Error("active project limit reached"));
    render(<ProjectsCard token="jwt" />);
    await screen.findByText("Spring promo launch");
    fireEvent.change(
      screen.getByPlaceholderText(/What should the team accomplish/),
      { target: { value: "Launch a fall promotion for detailing" } }
    );
    fireEvent.click(screen.getByText("Plan project"));
    expect(
      await screen.findByText("active project limit reached")
    ).toBeInTheDocument();
  });
});
