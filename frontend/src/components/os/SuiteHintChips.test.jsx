import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { useRef, useState } from "react";
import { describe, it, expect } from "vitest";

import SuiteHintChips from "./SuiteHintChips";

// Mirror of how AgentOS.jsx wires the chips: chip click populates the
// composer textarea and focuses it. Asserting against the rendered textarea
// keeps these tests on observable behavior.
function Harness({ disabled }) {
  const [composer, setComposer] = useState("");
  const composerRef = useRef(null);
  return (
    <div>
      <SuiteHintChips
        onSelectPrompt={setComposer}
        composerRef={composerRef}
        disabled={disabled}
      />
      <textarea
        ref={composerRef}
        value={composer}
        onChange={(e) => setComposer(e.target.value)}
        placeholder="Describe a task"
      />
    </div>
  );
}

describe("SuiteHintChips", () => {
  it("renders the fast-path chips", () => {
    render(<Harness />);
    expect(screen.getByText("Ask your data")).toBeInTheDocument();
    expect(screen.getByText("Start a project")).toBeInTheDocument();
    expect(screen.getByText("Weekly numbers")).toBeInTheDocument();
  });

  it("fills the composer with the BI question and focuses it", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("Ask your data"));
    const composer = screen.getByPlaceholderText("Describe a task");
    expect(composer).toHaveValue("How many leads did we get this week?");
    expect(composer).toHaveFocus();
  });

  it("fills the composer with the project trigger phrase for editing", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("Start a project"));
    expect(screen.getByPlaceholderText("Describe a task")).toHaveValue(
      "Start a project: ",
    );
  });

  it("leaves the composer untouched while disabled", () => {
    render(<Harness disabled />);
    fireEvent.click(screen.getByText("Ask your data"));
    expect(screen.getByPlaceholderText("Describe a task")).toHaveValue("");
  });
});
