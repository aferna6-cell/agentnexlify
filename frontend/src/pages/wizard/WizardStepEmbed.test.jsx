import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import WizardStepEmbed from "./WizardStepEmbed";

function renderStep(websiteUrl) {
  return render(
    <WizardStepEmbed
      wizardData={{ website_url: websiteUrl, business_name: "Salon" }}
      token={null}
      tenantId={null}
    />,
  );
}

describe("WizardStepEmbed connect deep link", () => {
  it("opens the existing website connect route with the submitted url", () => {
    renderStep("https://salon.example/book");
    expect(screen.getByTestId("onboarding-connect-link")).toHaveAttribute(
      "href",
      "/dashboard/website-connect?url=" +
        encodeURIComponent("https://salon.example/book"),
    );
    expect(screen.getByText("Your embed code")).toBeInTheDocument();
  });

  it("links to connect without a query when onboarding has no website", () => {
    renderStep("");
    expect(screen.getByTestId("onboarding-connect-link")).toHaveAttribute(
      "href",
      "/dashboard/website-connect",
    );
  });

  it("adds https when the onboarding website has no scheme", () => {
    renderStep("salon.example");
    expect(screen.getByTestId("onboarding-connect-link")).toHaveAttribute(
      "href",
      "/dashboard/website-connect?url=" +
        encodeURIComponent("https://salon.example/"),
    );
  });

  it("does not put a non-http url on the connect link", () => {
    renderStep("ftp://files.example/widget");
    expect(screen.getByTestId("onboarding-connect-link")).toHaveAttribute(
      "href",
      "/dashboard/website-connect",
    );
  });

  it("does not put a javascript url on the connect link", () => {
    renderStep("javascript:alert(1)");
    expect(screen.getByTestId("onboarding-connect-link")).toHaveAttribute(
      "href",
      "/dashboard/website-connect",
    );
  });

  it("does not put an unparseable website on the connect link", () => {
    renderStep("not a url");
    expect(screen.getByTestId("onboarding-connect-link")).toHaveAttribute(
      "href",
      "/dashboard/website-connect",
    );
  });
});
