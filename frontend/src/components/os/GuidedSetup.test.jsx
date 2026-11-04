import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/os", () => ({
  createOsTask: vi.fn(),
}));
vi.mock("../../utils/api/dashboard", () => ({
  updateTenantSettings: vi.fn(),
}));

import { createOsTask } from "../../utils/api/os";
import { updateTenantSettings } from "../../utils/api/dashboard";
import GuidedSetup from "./GuidedSetup";

beforeEach(() => {
  createOsTask.mockReset().mockResolvedValue({ id: "task-1" });
  updateTenantSettings.mockReset().mockResolvedValue({ ok: true });
});

describe("GuidedSetup", () => {
  it("asks the business type before offering tasks", () => {
    render(<GuidedSetup token="jwt" tenantId="t1" businessType="" />);
    expect(
      screen.getByText(
        "What kind of business is this? Then you can turn on a few ready-made tasks. Each one drafts work for you to review. Nothing sends on its own.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Low-stock alert")).not.toBeInTheDocument();
  });

  it("offers warehouse tasks and creates one on click", async () => {
    render(<GuidedSetup token="jwt" tenantId="t1" businessType="" />);
    fireEvent.click(screen.getByText("Warehouse / distribution"));
    expect(await screen.findByText("Low-stock alert")).toBeInTheDocument();
    expect(screen.getByText("Late-shipment follow-up")).toBeInTheDocument();
    expect(screen.getByText("Supplier reorder")).toBeInTheDocument();
    expect(screen.getByText("Daily ops summary")).toBeInTheDocument();
    expect(screen.getByText("Shift and safety reminders")).toBeInTheDocument();
    expect(screen.getByText("Returns handling")).toBeInTheDocument();
    expect(updateTenantSettings).toHaveBeenCalledWith("t1", "jwt", {
      business_type: "warehouse",
    });

    const addButtons = screen.getAllByRole("button", { name: "Add" });
    fireEvent.click(addButtons[0]);
    await waitFor(() => expect(createOsTask).toHaveBeenCalledTimes(1));
    const payload = createOsTask.mock.calls[0][1];
    expect(payload.prompt.toLowerCase()).toContain("low-stock");
    expect(payload.department).toBe("people");
    expect(await screen.findByText("Added")).toBeInTheDocument();
  });

  it("skips the question when the business type is already known", () => {
    render(<GuidedSetup token="jwt" tenantId="t1" businessType="warehouse" />);
    expect(screen.getByText("Low-stock alert")).toBeInTheDocument();
    expect(
      screen.queryByText(/What kind of business is this/),
    ).not.toBeInTheDocument();
  });
});
