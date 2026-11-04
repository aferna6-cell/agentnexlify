import { describe, it, expect } from "vitest";
import { aiGenerationUnavailable } from "./aiAvailability";

describe("aiGenerationUnavailable", () => {
  it("is false for an ordinary reply", () => {
    expect(
      aiGenerationUnavailable(
        [{ role: "assistant", content: "Draft ready for review: Follow-up" }],
        [],
      ),
    ).toBe(false);
  });

  it("is true when the engine says it is offline", () => {
    expect(
      aiGenerationUnavailable(
        [
          {
            role: "assistant",
            content:
              "Your message is saved, but the agent engine is temporarily unavailable.",
          },
        ],
        [],
      ),
    ).toBe(true);
  });

  it("is true when the latest draft was composed locally", () => {
    expect(
      aiGenerationUnavailable(
        [
          {
            id: "a1",
            role: "assistant",
            content: "Draft ready",
            agent_run_id: "r1",
          },
        ],
        [{ id: "r1", deliverable: { metadata: { source: "local" } } }],
      ),
    ).toBe(true);
  });

  it("ignores an older offline turn once a live reply arrives", () => {
    expect(
      aiGenerationUnavailable(
        [
          {
            role: "assistant",
            content: "I'm running in offline mode right now.",
          },
          { role: "user", content: "try again" },
          {
            role: "assistant",
            content: "Draft ready for review: Summary",
            agent_run_id: "r2",
          },
        ],
        [{ id: "r2", deliverable: { metadata: { source: "model" } } }],
      ),
    ).toBe(false);
  });
});
