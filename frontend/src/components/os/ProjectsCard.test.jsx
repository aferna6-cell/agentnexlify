import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  listOsProjects: vi.fn(),
  createOsProject: vi.fn(),
  fetchOsProject: vi.fn(),
  approveOsProject: vi.fn(),
  cancelOsProject: vi.fn(),
  approveOsDeliverable: vi.fn(),
  rejectOsDeliverable: vi.fn(),
}));

import {
  approveOsDeliverable,
  approveOsProject,
  cancelOsProject,
  createOsProject,
  fetchOsProject,
  listOsProjects,
  rejectOsDeliverable,
} from "../../utils/api/os";
import ProjectsCard from "./ProjectsCard";

const DRAFT = { id: "p1", title: "Spring promo launch", status: "draft" };

beforeEach(() => {
  listOsProjects.mockReset();
  createOsProject.mockReset();
  fetchOsProject.mockReset();
  approveOsProject.mockReset();
  cancelOsProject.mockReset();
  approveOsDeliverable.mockReset();
  rejectOsDeliverable.mockReset();
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

  it("approves a step's pending draft inline from the timeline", async () => {
    const running = { id: "p1", title: "Spring promo launch", status: "running" };
    listOsProjects.mockResolvedValue({ projects: [running] });
    const awaiting = {
      id: "s1",
      position: 1,
      department: "marketing",
      objective: "Draft the promo email",
      status: "awaiting_approval",
      agent_run_id: "run1",
      deliverable_status: "pending_approval",
      deliverable_title: "Promo email draft",
    };
    fetchOsProject.mockResolvedValue({ project: running, steps: [awaiting] });
    approveOsDeliverable.mockResolvedValue({});
    render(<ProjectsCard token="jwt" />);
    await screen.findByText("Spring promo launch");
    fireEvent.click(screen.getByText("Steps"));
    expect(
      await screen.findByText("Produced: Promo email draft")
    ).toBeInTheDocument();
    fireEvent.click(screen.getByText("Approve draft"));
    await waitFor(() =>
      expect(approveOsDeliverable).toHaveBeenCalledWith("jwt", "run1")
    );
  });

  it("rejects a step's pending draft inline", async () => {
    const running = { id: "p1", title: "Spring promo launch", status: "running" };
    listOsProjects.mockResolvedValue({ projects: [running] });
    fetchOsProject.mockResolvedValue({
      project: running,
      steps: [
        {
          id: "s1",
          position: 1,
          department: "sales",
          objective: "Draft the outreach text",
          status: "awaiting_approval",
          agent_run_id: "run2",
          deliverable_status: "pending_approval",
        },
      ],
    });
    rejectOsDeliverable.mockResolvedValue({});
    render(<ProjectsCard token="jwt" />);
    await screen.findByText("Spring promo launch");
    fireEvent.click(screen.getByText("Steps"));
    fireEvent.click(await screen.findByText("Reject"));
    await waitFor(() =>
      expect(rejectOsDeliverable).toHaveBeenCalledWith("jwt", "run2")
    );
  });

  it("offers no inline decision on steps without a pending deliverable", async () => {
    fetchOsProject.mockResolvedValue({
      project: DRAFT,
      steps: [
        {
          id: "s1",
          position: 1,
          department: "marketing",
          objective: "Draft the promo email",
          status: "done",
          agent_run_id: "run1",
          deliverable_status: "approved",
          deliverable_title: "Promo email draft",
        },
      ],
    });
    render(<ProjectsCard token="jwt" />);
    await screen.findByText("Spring promo launch");
    fireEvent.click(screen.getByText("Steps"));
    await screen.findByText("Produced: Promo email draft");
    expect(screen.queryByText("Approve draft")).not.toBeInTheDocument();
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
