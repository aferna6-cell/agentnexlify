import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  listOsTasks: vi.fn(),
  createOsTask: vi.fn(),
  updateOsTask: vi.fn(),
  deleteOsTask: vi.fn(),
  fetchOsTaskSuggestions: vi.fn(),
}));

import {
  createOsTask,
  deleteOsTask,
  fetchOsTaskSuggestions,
  listOsTasks,
  updateOsTask,
} from "../../utils/api/os";
import ScheduledTasksCard from "./ScheduledTasksCard";

const TASK = {
  id: "t1",
  department: "marketing",
  prompt: "Draft this week's promo",
  interval_days: 7,
  enabled: true,
  last_run_at: "2026-07-14T09:00:00Z",
};

beforeEach(() => {
  listOsTasks.mockReset();
  createOsTask.mockReset();
  updateOsTask.mockReset();
  deleteOsTask.mockReset();
  fetchOsTaskSuggestions.mockReset();
  fetchOsTaskSuggestions.mockResolvedValue({ suggestions: [] });
  listOsTasks.mockResolvedValue({
    tasks: [TASK],
    departments: ["marketing", "sales"],
  });
});

describe("ScheduledTasksCard", () => {
  it("lists existing tasks with cadence and last-run info", async () => {
    render(<ScheduledTasksCard token="jwt" />);
    expect(await screen.findByText("Draft this week's promo")).toBeInTheDocument();
    expect(screen.getByText(/every 7 days/)).toBeInTheDocument();
    expect(screen.getByText(/last ran 2026-07-14/)).toBeInTheDocument();
  });

  it("shows the empty state when there are no tasks", async () => {
    listOsTasks.mockResolvedValue({ tasks: [], departments: ["marketing"] });
    render(<ScheduledTasksCard token="jwt" />);
    expect(
      await screen.findByText(/No recurring tasks yet/)
    ).toBeInTheDocument();
  });

  it("creates a task from the form", async () => {
    createOsTask.mockResolvedValue({});
    render(<ScheduledTasksCard token="jwt" />);
    await screen.findByText("Draft this week's promo");
    fireEvent.change(
      screen.getByPlaceholderText(/What should the agent do/),
      { target: { value: "Send a weekly summary" } }
    );
    fireEvent.click(screen.getByText("Add task"));
    await waitFor(() => expect(createOsTask).toHaveBeenCalled());
    expect(createOsTask.mock.calls[0][1]).toMatchObject({
      department: "marketing",
      prompt: "Send a weekly summary",
      enabled: true,
    });
  });

  it("pauses a task via the toggle", async () => {
    updateOsTask.mockResolvedValue({});
    render(<ScheduledTasksCard token="jwt" />);
    await screen.findByText("Draft this week's promo");
    fireEvent.click(screen.getByText("Pause"));
    await waitFor(() =>
      expect(updateOsTask).toHaveBeenCalledWith("jwt", "t1", { enabled: false })
    );
  });

  it("deletes a task", async () => {
    deleteOsTask.mockResolvedValue({});
    render(<ScheduledTasksCard token="jwt" />);
    await screen.findByText("Draft this week's promo");
    fireEvent.click(screen.getByText("Delete"));
    await waitFor(() => expect(deleteOsTask).toHaveBeenCalledWith("jwt", "t1"));
  });

  it("offers one-click starter suggestions when the tenant has no tasks", async () => {
    listOsTasks.mockResolvedValue({ tasks: [], departments: ["marketing"] });
    fetchOsTaskSuggestions.mockResolvedValue({
      suggestions: [
        {
          label: "Weekly promo draft",
          department: "marketing",
          interval_days: 7,
          prompt: "Draft this week's promotional post for my coffee shop.",
        },
      ],
    });
    createOsTask.mockResolvedValue({});
    render(<ScheduledTasksCard token="jwt" />);
    expect(await screen.findByText("Weekly promo draft")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Add"));
    await waitFor(() =>
      expect(createOsTask).toHaveBeenCalledWith("jwt", {
        department: "marketing",
        prompt: "Draft this week's promotional post for my coffee shop.",
        interval_days: 7,
        enabled: true,
      })
    );
  });

  it("surfaces a load failure", async () => {
    listOsTasks.mockRejectedValue(new Error("boom"));
    render(<ScheduledTasksCard token="jwt" />);
    expect(
      await screen.findByText(/Could not load scheduled tasks/)
    ).toBeInTheDocument();
  });
});
