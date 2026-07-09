import { describe, it, expect } from "vitest";
import { leadTemperature } from "./leadTemperature";

describe("leadTemperature", () => {
  // --- null / undefined / missing ---
  it("returns New for null", () => {
    expect(leadTemperature(null)).toEqual({ emoji: "", label: "New", tone: "new" });
  });

  it("returns New for undefined", () => {
    expect(leadTemperature(undefined)).toEqual({ emoji: "", label: "New", tone: "new" });
  });

  // --- 0-100 scale ---
  it("returns hot for score 100 (0-100 scale)", () => {
    expect(leadTemperature(100)).toEqual({ emoji: "🔥", label: "Ready to book", tone: "hot" });
  });

  it("returns hot for score 75 (0-100 scale, boundary)", () => {
    expect(leadTemperature(75)).toEqual({ emoji: "🔥", label: "Ready to book", tone: "hot" });
  });

  it("returns warm for score 74 (0-100 scale)", () => {
    expect(leadTemperature(74)).toEqual({ emoji: "👀", label: "Just looking", tone: "warm" });
  });

  it("returns warm for score 45 (0-100 scale, boundary)", () => {
    expect(leadTemperature(45)).toEqual({ emoji: "👀", label: "Just looking", tone: "warm" });
  });

  it("returns cold for score 44 (0-100 scale)", () => {
    expect(leadTemperature(44)).toEqual({ emoji: "❄️", label: "Cold", tone: "cold" });
  });

  it("returns cold for score 1 (0-100 scale, above zero)", () => {
    expect(leadTemperature(1)).toEqual({ emoji: "❄️", label: "Cold", tone: "cold" });
  });

  it("returns New for score 0 (0-100 scale)", () => {
    expect(leadTemperature(0)).toEqual({ emoji: "", label: "New", tone: "new" });
  });

  // --- 0-10 scale ---
  it("returns hot for score 10 (0-10 scale)", () => {
    expect(leadTemperature(10)).toEqual({ emoji: "🔥", label: "Ready to book", tone: "hot" });
  });

  it("returns hot for score 8 (0-10 scale, >= 0.75 normalized)", () => {
    expect(leadTemperature(8)).toEqual({ emoji: "🔥", label: "Ready to book", tone: "hot" });
  });

  it("returns warm for score 7 (0-10 scale)", () => {
    expect(leadTemperature(7)).toEqual({ emoji: "👀", label: "Just looking", tone: "warm" });
  });

  it("returns warm for score 5 (0-10 scale, >= 0.45 normalized, boundary)", () => {
    expect(leadTemperature(5)).toEqual({ emoji: "👀", label: "Just looking", tone: "warm" });
  });

  it("returns cold for score 4 (0-10 scale)", () => {
    expect(leadTemperature(4)).toEqual({ emoji: "❄️", label: "Cold", tone: "cold" });
  });

  it("returns cold for score 1 (0-10 scale)", () => {
    expect(leadTemperature(1)).toEqual({ emoji: "❄️", label: "Cold", tone: "cold" });
  });

  it("returns New for score 0 (0-10 scale)", () => {
    expect(leadTemperature(0)).toEqual({ emoji: "", label: "New", tone: "new" });
  });
});
