import { describe, it, expect } from "vitest";
import {
  BUSINESS_TYPES,
  resolveBusinessType,
  templatesFor,
} from "./starterTemplates";

const WAREHOUSE_LABELS = [
  "Low-stock alert",
  "Late-shipment follow-up",
  "Supplier reorder",
  "Daily ops summary",
  "Shift and safety reminders",
  "Returns handling",
];

describe("starter templates", () => {
  it("offers 5 to 8 tasks for every business type", () => {
    for (const type of BUSINESS_TYPES) {
      const items = templatesFor(type.id);
      expect(items.length).toBeGreaterThanOrEqual(5);
      expect(items.length).toBeLessThanOrEqual(8);
    }
  });

  it("includes the warehouse task set", () => {
    const labels = templatesFor("warehouse").map((item) => item.label);
    for (const label of WAREHOUSE_LABELS) {
      expect(labels).toContain(label);
    }
  });

  it("maps a saved warehouse business type onto the warehouse set", () => {
    expect(resolveBusinessType("warehouse_distribution")).toBe("warehouse");
    expect(templatesFor("Fulfillment warehouse")[0].label).toBe(
      "Low-stock alert",
    );
  });

  it("keeps daily ops as a summary, not a customer appointment text", () => {
    const daily = templatesFor("warehouse").find(
      (item) => item.label === "Daily ops summary",
    );
    expect(daily.prompt.toLowerCase()).toContain("summary");
    expect(daily.prompt.toLowerCase()).not.toContain("your appointment");
    expect(daily.department).toBe("accounting");
  });
});
