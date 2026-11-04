import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ThreadList from "./ThreadList";

const NOW = new Date().toISOString();

describe("ThreadList", () => {
  it("collapses repeated scheduled runs and expands them", () => {
    const onSelect = vi.fn();
    render(
      <ThreadList
        activeThreadId=""
        onSelect={onSelect}
        threads={[
          {
            id: "s1",
            title: "Scheduled: Prepare my weekly business summary for the shop",
            updated_at: NOW,
          },
          {
            id: "s2",
            title: "Scheduled: Prepare my weekly business summary for the shop",
            updated_at: NOW,
          },
        ]}
      />,
    );
    expect(
      screen.getAllByText(/Prepare my weekly business summary for the shop/),
    ).toHaveLength(1);
    expect(screen.getByText("2 scheduled runs")).toBeInTheDocument();
    fireEvent.click(screen.getByText("2 scheduled runs"));
    expect(
      screen.getAllByText(/Prepare my weekly business summary for the shop/)
        .length,
    ).toBeGreaterThan(1);
    fireEvent.click(screen.getAllByText(/just now|m ago|h ago/)[0]);
    expect(onSelect).toHaveBeenCalled();
  });

  it("filters the list by search", () => {
    render(
      <ThreadList
        activeThreadId="t1"
        onSelect={() => {}}
        threads={[
          { id: "t1", title: "Call Mike back", updated_at: NOW },
          { id: "t2", title: "Invoice the Hendersons", updated_at: NOW },
        ]}
      />,
    );
    fireEvent.change(screen.getByLabelText("Search tasks"), {
      target: { value: "Hendersons" },
    });
    expect(screen.getByText("Invoice the Hendersons")).toBeInTheDocument();
    expect(screen.queryByText("Call Mike back")).not.toBeInTheDocument();
  });
});
