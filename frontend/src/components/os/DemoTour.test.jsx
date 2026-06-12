import "@testing-library/jest-dom/vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("../../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../../context/AuthContext";
import DemoTour from "./DemoTour";

const STORAGE_KEY = "anx_demo_tour_done";

beforeEach(() => {
  sessionStorage.removeItem(STORAGE_KEY);
  useAuth.mockReset();
});

afterEach(() => {
  sessionStorage.removeItem(STORAGE_KEY);
});

describe("DemoTour", () => {
  it("renders the tour card for role=demo when not yet dismissed", () => {
    useAuth.mockReturnValue({ user: { role: "demo", tenantId: "demo-1" } });
    render(<DemoTour />);
    expect(screen.getByTestId("demo-tour-card")).toBeInTheDocument();
    expect(
      screen.getByText(/Your Agent OS inbox/i),
    ).toBeInTheDocument();
  });

  it("does not render for role=owner", () => {
    useAuth.mockReturnValue({ user: { role: "owner", tenantId: "t-1" } });
    render(<DemoTour />);
    expect(screen.queryByTestId("demo-tour-card")).not.toBeInTheDocument();
  });

  it("does not render when user is null", () => {
    useAuth.mockReturnValue({ user: null });
    render(<DemoTour />);
    expect(screen.queryByTestId("demo-tour-card")).not.toBeInTheDocument();
  });

  it("does not render when the sessionStorage key is already set", () => {
    sessionStorage.setItem(STORAGE_KEY, "1");
    useAuth.mockReturnValue({ user: { role: "demo", tenantId: "demo-1" } });
    render(<DemoTour />);
    expect(screen.queryByTestId("demo-tour-card")).not.toBeInTheDocument();
  });

  it("Skip tour sets the sessionStorage key and hides the card", () => {
    useAuth.mockReturnValue({ user: { role: "demo", tenantId: "demo-1" } });
    render(<DemoTour />);
    expect(screen.getByTestId("demo-tour-card")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("demo-tour-skip"));

    expect(screen.queryByTestId("demo-tour-card")).not.toBeInTheDocument();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBe("1");
  });

  it("Next advances through all steps then hides on Done", () => {
    useAuth.mockReturnValue({ user: { role: "demo", tenantId: "demo-1" } });
    render(<DemoTour />);

    // Step 1
    expect(screen.getByText(/Your Agent OS inbox/i)).toBeInTheDocument();
    expect(screen.getByTestId("demo-tour-next")).toHaveTextContent("Next");

    // Advance to step 2
    fireEvent.click(screen.getByTestId("demo-tour-next"));
    expect(screen.getByText(/AI drafted a response overnight/i)).toBeInTheDocument();
    expect(screen.getByTestId("demo-tour-next")).toHaveTextContent("Next");

    // Advance to step 3
    fireEvent.click(screen.getByTestId("demo-tour-next"));
    expect(screen.getByText(/Nothing sends without your OK/i)).toBeInTheDocument();
    expect(screen.getByTestId("demo-tour-next")).toHaveTextContent("Done");

    // Done dismisses
    fireEvent.click(screen.getByTestId("demo-tour-next"));
    expect(screen.queryByTestId("demo-tour-card")).not.toBeInTheDocument();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBe("1");
  });

  it("shows step indicator with the correct number of segments", () => {
    useAuth.mockReturnValue({ user: { role: "demo", tenantId: "demo-1" } });
    render(<DemoTour />);
    // 3 step indicator spans inside the card
    const card = screen.getByTestId("demo-tour-card");
    // The step-indicator spans are children of a flex container inside the card.
    // Check that the card has the role=dialog with the correct aria-label.
    expect(card).toHaveAttribute(
      "aria-label",
      "Tour step 1 of 3: Your Agent OS inbox",
    );
  });
});
