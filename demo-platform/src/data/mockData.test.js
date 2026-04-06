import { describe, expect, it } from "vitest";

import {
  formatTimeAgo,
  getScoreEmoji,
  pipelineStages,
} from "./mockData";

describe("mockData utilities", () => {
  it("formats relative time labels", () => {
    expect(formatTimeAgo(0)).toBe("Just now");
    expect(formatTimeAgo(59)).toBe("59 min ago");
    expect(formatTimeAgo(60)).toBe("1 hour ago");
    expect(formatTimeAgo(180)).toBe("3 hours ago");
    expect(formatTimeAgo(1500)).toBe("Yesterday");
    expect(formatTimeAgo(4320)).toBe("3 days ago");
  });

  it("maps lead scores to expected emoji", () => {
    expect(getScoreEmoji("hot")).toBe("🔴");
    expect(getScoreEmoji("warm")).toBe("🟡");
    expect(getScoreEmoji("cold")).toBe("🔵");
  });

  it("keeps a closed stage in the pipeline", () => {
    expect(pipelineStages.some((stage) => stage.key === "closed")).toBe(true);
  });
});
