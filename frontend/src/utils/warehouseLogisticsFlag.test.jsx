import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BusinessInformationCard } from "../pages/settings/BusinessSettingsCards";
import WizardExpressSetup from "../pages/wizard/WizardExpressSetup";
import WizardStepBusiness from "../pages/wizard/WizardStepBusiness";

const settingsForm = {
  business_name: "Northwind",
  business_type: "",
  city: "Dallas",
  owner_name: "Avery",
};

function renderSignupAndSettings() {
  render(
    <BusinessInformationCard
      form={settingsForm}
      handleChange={() => () => {}}
      handleSave={() => {}}
      saving={false}
      saved={false}
      saveError=""
    />,
  );
  render(<WizardExpressSetup user={{}} token="jwt" onCustomize={() => {}} />);
  render(<WizardStepBusiness wizardData={{}} onNext={() => {}} />);
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("warehouse logistics option", () => {
  it("stays hidden in signup and settings while the flag is off", () => {
    vi.stubEnv("VITE_WAREHOUSE_LOGISTICS_ENABLED", "");
    renderSignupAndSettings();
    expect(
      screen.queryAllByRole("option", { name: "Warehouse / Logistics" }),
    ).toHaveLength(0);
  });

  it("appears in signup and settings only when the flag is on", () => {
    vi.stubEnv("VITE_WAREHOUSE_LOGISTICS_ENABLED", "1");
    renderSignupAndSettings();
    expect(
      screen.getAllByRole("option", { name: "Warehouse / Logistics" }),
    ).toHaveLength(3);
  });
});
