import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../utils/api/websiteConnect", () => ({
  getWebsiteConnection: vi.fn(),
}));

import { getWebsiteConnection } from "../../utils/api/websiteConnect";
import WidgetEmbed from "./WidgetEmbed";

beforeEach(() => {
  getWebsiteConnection.mockReset();
});

describe("WidgetEmbed connection copy", () => {
  it("uses the connected success sentence", async () => {
    getWebsiteConnection.mockResolvedValue({
      status: "connected",
      connection: { status: "connected", website_url: "https://salon.example" },
    });
    render(
      <WidgetEmbed
        apiKey="wk_test"
        tenantId="ten1"
        token="jwt"
        widgetConfig={{ greeting_message: "Hi", primary_color: "#00BFFF" }}
      />,
    );
    expect(
      await screen.findByText(
        "Your website is connected and your AI receptionist is live.",
      ),
    ).toBeInTheDocument();
  });

  it("does not claim the receptionist is live before connect", async () => {
    getWebsiteConnection.mockResolvedValue({
      connection: null,
      status: "not_started",
    });
    render(
      <WidgetEmbed
        apiKey="wk_test"
        tenantId="ten1"
        token="jwt"
        widgetConfig={{}}
      />,
    );
    expect(
      await screen.findByText("Not verified on your website yet"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        "Your website is connected and your AI receptionist is live.",
      ),
    ).not.toBeInTheDocument();
  });
});
