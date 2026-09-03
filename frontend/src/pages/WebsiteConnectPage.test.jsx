import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let mockAuth;
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("../utils/api/websiteConnect", () => ({
  getWebsiteConnection: vi.fn(),
  connectWebsite: vi.fn(),
  verifyWebsiteConnection: vi.fn(),
  wordpressPluginDownloadUrl: () => "https://api.example/wordpress-plugin",
}));

vi.mock("../utils/api/dashboard", () => ({
  fetchDashboard: vi.fn(),
}));

vi.mock("../components/SkeletonLoader", () => ({
  default: () => <div data-testid="skeleton" />,
}));

import {
  getWebsiteConnection,
  connectWebsite,
  verifyWebsiteConnection,
} from "../utils/api/websiteConnect";
import { fetchDashboard } from "../utils/api/dashboard";
import WebsiteConnectPage from "./WebsiteConnectPage";

beforeEach(() => {
  mockAuth = { user: { tenantId: "ten1" }, token: "jwt" };
  getWebsiteConnection.mockReset();
  connectWebsite.mockReset();
  verifyWebsiteConnection.mockReset();
  fetchDashboard.mockReset();
  fetchDashboard.mockResolvedValue({ widget_api_key: "wk_test_key" });
});

describe("WebsiteConnectPage", () => {
  it("does not claim connected before a verified row exists", async () => {
    getWebsiteConnection.mockResolvedValue({
      connection: null,
      status: "not_started",
    });
    render(<WebsiteConnectPage />);
    expect(await screen.findByText("Connect your website")).toBeInTheDocument();
    expect(screen.getByTestId("connect-status")).toHaveTextContent(
      "Connect your website",
    );
    expect(
      screen.queryByText("AI receptionist is live"),
    ).not.toBeInTheDocument();
  });

  it("shows live only after the API reports connected", async () => {
    getWebsiteConnection.mockResolvedValue({
      status: "connected",
      connection: {
        website_url: "https://salon.example",
        platform: "wordpress",
        status: "connected",
        verification_detail: "Live HTML includes this tenant's widget key.",
        next_action: { title: "AI receptionist is live", steps: [] },
      },
    });
    render(<WebsiteConnectPage />);
    expect(
      await screen.findByText("AI receptionist is live"),
    ).toBeInTheDocument();
    expect(screen.getByText("https://salon.example")).toBeInTheDocument();
  });

  it("submits the URL without any password field", async () => {
    getWebsiteConnection.mockResolvedValue({
      connection: null,
      status: "not_started",
    });
    connectWebsite.mockResolvedValue({
      id: "row1",
      website_url: "https://salon.example",
      platform: "wordpress",
      status: "needs_action",
      next_action: {
        title: "Install the WordPress plugin",
        steps: ["Download the plugin"],
        snippet_fallback: true,
      },
    });
    render(<WebsiteConnectPage />);
    const input = await screen.findByLabelText("Site address");
    fireEvent.change(input, { target: { value: "https://salon.example" } });
    fireEvent.click(screen.getByRole("button", { name: "Connect website" }));
    await waitFor(() => {
      expect(connectWebsite).toHaveBeenCalledWith("jwt", {
        website_url: "https://salon.example",
        platform: undefined,
      });
    });
    const sent = connectWebsite.mock.calls[0][1];
    expect(sent).not.toHaveProperty("password");
    expect(
      await screen.findByText("Install the WordPress plugin"),
    ).toBeInTheDocument();
  });

  it("verify uses the existing connection instead of marking installed locally", async () => {
    getWebsiteConnection.mockResolvedValue({
      status: "needs_action",
      connection: {
        website_url: "https://salon.example",
        platform: "wix",
        status: "needs_action",
        next_action: {
          title: "Add the snippet in Wix Custom Code",
          steps: ["Paste"],
          snippet_fallback: true,
        },
      },
    });
    verifyWebsiteConnection.mockResolvedValue({
      id: "row1",
      website_url: "https://salon.example",
      platform: "wix",
      status: "needs_action",
      verification_detail: "This tenant's widget key was not found.",
      next_action: {
        title: "Add the snippet in Wix Custom Code",
        steps: ["Paste"],
        snippet_fallback: true,
      },
    });
    render(<WebsiteConnectPage />);
    const verify = await screen.findByRole("button", { name: "Verify now" });
    fireEvent.click(verify);
    await waitFor(() => {
      expect(verifyWebsiteConnection).toHaveBeenCalledWith("jwt");
    });
    expect(
      await screen.findByText("This tenant's widget key was not found."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("AI receptionist is live"),
    ).not.toBeInTheDocument();
  });
});
