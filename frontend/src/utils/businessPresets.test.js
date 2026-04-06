import { describe, expect, it } from "vitest";

import { getPresetWidgetDefaults } from "./businessPresets";

describe("getPresetWidgetDefaults", () => {
  it("maps aliases to the correct preset", () => {
    const result = getPresetWidgetDefaults("plumbing", "Apex Home Services");

    expect(result.widget_bot_name).toBe("Apex Home Services Scheduling Desk");
    expect(result.widget_primary_color).toBe("#0f766e");
    expect(result.widget_greeting_message).toContain("Apex Home Services");
    expect(result.widget_position).toBe("bottom-right");
  });

  it("uses the real estate preset for realestate alias", () => {
    const result = getPresetWidgetDefaults("realestate", "Peak Realty");

    expect(result.widget_bot_name).toBe("Peak Realty Lead Desk");
    expect(result.widget_primary_color).toBe("#2563eb");
  });

  it("falls back to default preset and business name when values are missing", () => {
    const result = getPresetWidgetDefaults("", "   ");

    expect(result.widget_bot_name).toBe("Your Business Assistant");
    expect(result.widget_primary_color).toBe("#00BFFF");
    expect(result.widget_greeting_message).toContain("Your Business");
  });
});
