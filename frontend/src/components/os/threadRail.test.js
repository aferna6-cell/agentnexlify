import { describe, it, expect } from "vitest";
import { filterThreads, groupThreads, threadTitle } from "./threadRail";

const weekly = (id, title) => ({ id, title });

describe("thread rail", () => {
  it("shows the full stored title", () => {
    const title =
      "Scheduled: Prepare my weekly business summary for the warehouse team";
    expect(threadTitle(weekly("a", title))).toBe(title);
  });

  it("collapses repeated scheduled runs and keeps the longest title", () => {
    const body =
      "Prepare my weekly business summary for the warehouse team and note anything that needs attention today";
    const groups = groupThreads([
      weekly("new", `Scheduled: ${body}`),
      weekly("old", `Scheduled: ${body.slice(0, 60)}`),
      weekly("chat", "Call Mike back"),
    ]);
    expect(groups).toHaveLength(2);
    expect(groups[0].kind).toBe("group");
    expect(groups[0].threads).toHaveLength(2);
    expect(groups[0].title).toContain("warehouse team");
    expect(groups[1].title).toBe("Call Mike back");
  });

  it("searches by the full title", () => {
    const threads = [
      weekly("a", "Scheduled: Prepare my weekly business summary"),
      weekly("b", "Call Mike back"),
    ];
    expect(filterThreads(threads, "weekly").map((t) => t.id)).toEqual(["a"]);
    expect(filterThreads(threads, "mike").map((t) => t.id)).toEqual(["b"]);
    expect(filterThreads(threads, "")).toHaveLength(2);
  });
});
