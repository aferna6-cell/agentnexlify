import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../utils/api/qualifier", () => ({
  fetchQualifierSettings: vi.fn(),
  updateQualifierSettings: vi.fn(),
}));

import {
  fetchQualifierSettings,
  updateQualifierSettings,
} from "../utils/api/qualifier";
import AgentQualifierSettings from "./AgentQualifierSettings";

const PROPS = { tenantId: "ten1", token: "jwt" };

beforeEach(() => {
  fetchQualifierSettings.mockReset();
  updateQualifierSettings.mockReset();
});

describe("AgentQualifierSettings", () => {
  it("loads settings on mount and reflects enabled + threshold", async () => {
    fetchQualifierSettings.mockResolvedValue({
      qualifier_enabled: true,
      qualifier_min_intent: 5,
    });

    render(<AgentQualifierSettings {...PROPS} />);

    const toggle = await screen.findByRole("switch", {
      name: "Run AI qualification",
    });
    expect(toggle).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(fetchQualifierSettings).toHaveBeenCalledWith("ten1", "jwt");
  });

  it("shows 'All' when the threshold is 0", async () => {
    fetchQualifierSettings.mockResolvedValue({
      qualifier_enabled: true,
      qualifier_min_intent: 0,
    });
    render(<AgentQualifierSettings {...PROPS} />);
    expect(await screen.findByText("All")).toBeInTheDocument();
  });

  it("treats qualifier_enabled false as off", async () => {
    fetchQualifierSettings.mockResolvedValue({
      qualifier_enabled: false,
      qualifier_min_intent: 0,
    });
    render(<AgentQualifierSettings {...PROPS} />);
    const toggle = await screen.findByRole("switch");
    expect(toggle).toHaveAttribute("aria-checked", "false");
  });

  it("toggles the enabled switch on click", async () => {
    fetchQualifierSettings.mockResolvedValue({
      qualifier_enabled: true,
      qualifier_min_intent: 0,
    });
    render(<AgentQualifierSettings {...PROPS} />);
    const toggle = await screen.findByRole("switch");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-checked", "false");
  });

  it("saves the current state and confirms", async () => {
    fetchQualifierSettings.mockResolvedValue({
      qualifier_enabled: true,
      qualifier_min_intent: 3,
    });
    updateQualifierSettings.mockResolvedValue({});

    render(<AgentQualifierSettings {...PROPS} />);
    await screen.findByRole("switch");

    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(updateQualifierSettings).toHaveBeenCalledWith(
        "ten1",
        { qualifier_enabled: true, qualifier_min_intent: 3 },
        "jwt",
      ),
    );
    expect(await screen.findByText("Saved")).toBeInTheDocument();
  });

  it("surfaces the pre-migration 503 message on save", async () => {
    fetchQualifierSettings.mockResolvedValue({
      qualifier_enabled: true,
      qualifier_min_intent: 0,
    });
    updateQualifierSettings.mockRejectedValue({ status: 503 });

    render(<AgentQualifierSettings {...PROPS} />);
    await screen.findByRole("switch");
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(
      await screen.findByText(/aren't available yet/i),
    ).toBeInTheDocument();
  });

  it("shows a load error when the fetch fails", async () => {
    fetchQualifierSettings.mockRejectedValue(new Error("nope"));
    render(<AgentQualifierSettings {...PROPS} />);
    expect(
      await screen.findByText("Could not load qualifier settings."),
    ).toBeInTheDocument();
  });
});
