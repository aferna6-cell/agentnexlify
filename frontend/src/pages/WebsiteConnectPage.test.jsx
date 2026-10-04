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

const CONNECTED_COPY =
  "Your website is connected and your AI receptionist is live.";

beforeEach(() => {
  mockAuth = { user: { tenantId: "ten1" }, token: "jwt" };
  getWebsiteConnection.mockReset();
  connectWebsite.mockReset();
  verifyWebsiteConnection.mockReset();
  fetchDashboard.mockReset();
  fetchDashboard.mockResolvedValue({ widget_api_key: "wk_test_key" });
  window.history.replaceState({}, "", "/dashboard/website-connect");
});

describe("WebsiteConnectPage", () => {
  it("does not claim connected before a verified row exists", async () => {
    getWebsiteConnection.mockResolvedValue({
      connection: null,
      status: "not_started",
    });
    render(<WebsiteConnectPage />);
    expect(await screen.findByTestId("connect-status-label")).toHaveTextContent(
      "Connect your website",
    );
    expect(screen.getByTestId("connect-status-reason")).toHaveTextContent(
      "Enter your website address",
    );
    expect(screen.queryByText(CONNECTED_COPY)).not.toBeInTheDocument();
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
    expect(await screen.findByTestId("connect-status-label")).toHaveTextContent(
      CONNECTED_COPY,
    );
    expect(
      screen.queryByTestId("connect-status-reason"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("connect-status")).toHaveTextContent(
      "https://salon.example",
    );
    expect(screen.getByTestId("connect-status")).toHaveTextContent(
      "Live HTML includes this tenant's widget key.",
    );
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
    expect(screen.queryByText(CONNECTED_COPY)).not.toBeInTheDocument();
  });

  it("renders every connection status with an actionable reason until connected", async () => {
    const cases = [
      {
        payload: { connection: null, status: "not_started" },
        label: "Connect your website",
        reason: "Enter your website address",
      },
      {
        payload: {
          status: "needs_action",
          connection: {
            website_url: "https://salon.example",
            platform: "custom",
            status: "needs_action",
          },
        },
        label: "Install the widget, then verify",
        reason: "Finish the platform step below",
      },
      {
        payload: {
          status: "verifying",
          connection: {
            website_url: "https://salon.example",
            platform: "wordpress",
            status: "verifying",
          },
        },
        label: "Verifying your website",
        reason: "Checking the URL you submitted",
      },
      {
        payload: {
          status: "failed",
          connection: {
            website_url: "https://salon.example",
            platform: "wix",
            status: "failed",
          },
        },
        label: "We could not verify this site yet",
        reason: "We could not reach that page",
      },
    ];
    for (const item of cases) {
      getWebsiteConnection.mockResolvedValue(item.payload);
      const view = render(<WebsiteConnectPage />);
      expect(
        await screen.findByTestId("connect-status-label"),
      ).toHaveTextContent(item.label);
      expect(screen.getByTestId("connect-status-reason")).toHaveTextContent(
        item.reason,
      );
      expect(screen.queryByText(CONNECTED_COPY)).not.toBeInTheDocument();
      view.unmount();
    }
  });

  it("shows verifying while the check is in flight and then the live sentence", async () => {
    getWebsiteConnection.mockResolvedValue({
      status: "needs_action",
      connection: {
        website_url: "https://salon.example",
        platform: "wix",
        status: "needs_action",
        verification_detail:
          "Checked the live site. This tenant's widget key was not found.",
        next_action: {
          title: "Add the snippet in Wix Custom Code",
          steps: ["Paste"],
          snippet_fallback: true,
        },
      },
    });
    let resolveVerify;
    verifyWebsiteConnection.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveVerify = resolve;
        }),
    );
    render(<WebsiteConnectPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Verify now" }));
    expect(await screen.findByTestId("connect-status-label")).toHaveTextContent(
      "Verifying your website",
    );
    expect(screen.getByTestId("connect-status-reason")).toHaveTextContent(
      "Checking the URL you submitted",
    );
    expect(
      screen.queryByText(/widget key was not found/),
    ).not.toBeInTheDocument();
    resolveVerify({
      id: "row1",
      website_url: "https://salon.example",
      platform: "wix",
      status: "connected",
      verification_detail: "Live HTML includes this tenant's widget key.",
    });
    expect(await screen.findByTestId("connect-status-label")).toHaveTextContent(
      CONNECTED_COPY,
    );
    expect(
      screen.queryByTestId("connect-status-reason"),
    ).not.toBeInTheDocument();
  });

  it("prefills the onboarding url and never treats that link as connected", async () => {
    window.history.replaceState(
      {},
      "",
      "/dashboard/website-connect?url=" +
        encodeURIComponent("https://from-onboarding.example/book"),
    );
    getWebsiteConnection.mockResolvedValue({
      connection: null,
      status: "not_started",
    });
    render(<WebsiteConnectPage />);
    expect(await screen.findByLabelText("Site address")).toHaveValue(
      "https://from-onboarding.example/book",
    );
    expect(screen.getByTestId("connect-status-label")).toHaveTextContent(
      "Connect your website",
    );
  });

  it("adds https when the onboarding deep link omits a scheme", async () => {
    window.history.replaceState(
      {},
      "",
      "/dashboard/website-connect?url=salon.example",
    );
    getWebsiteConnection.mockResolvedValue({
      connection: null,
      status: "not_started",
    });
    render(<WebsiteConnectPage />);
    expect(await screen.findByLabelText("Site address")).toHaveValue(
      "https://salon.example/",
    );
  });

  it("ignores a non-http onboarding url", async () => {
    window.history.replaceState(
      {},
      "",
      "/dashboard/website-connect?url=" +
        encodeURIComponent("ftp://files.example/widget"),
    );
    getWebsiteConnection.mockResolvedValue({
      connection: null,
      status: "not_started",
    });
    render(<WebsiteConnectPage />);
    expect(await screen.findByLabelText("Site address")).toHaveValue("");
  });

  it("ignores a javascript onboarding url", async () => {
    window.history.replaceState(
      {},
      "",
      "/dashboard/website-connect?url=" +
        encodeURIComponent("javascript:alert(1)"),
    );
    getWebsiteConnection.mockResolvedValue({
      connection: null,
      status: "not_started",
    });
    render(<WebsiteConnectPage />);
    expect(await screen.findByLabelText("Site address")).toHaveValue("");
  });

  it("ignores an unparseable onboarding url", async () => {
    window.history.replaceState(
      {},
      "",
      "/dashboard/website-connect?url=" + encodeURIComponent("not a url"),
    );
    getWebsiteConnection.mockResolvedValue({
      connection: null,
      status: "not_started",
    });
    render(<WebsiteConnectPage />);
    expect(await screen.findByLabelText("Site address")).toHaveValue("");
  });

  it("does not replace this tenant's saved url with the onboarding query", async () => {
    window.history.replaceState(
      {},
      "",
      "/dashboard/website-connect?url=" +
        encodeURIComponent("https://other-tenant.example"),
    );
    getWebsiteConnection.mockResolvedValue({
      status: "needs_action",
      connection: {
        website_url: "https://salon.example",
        platform: "custom",
        status: "needs_action",
        verification_detail:
          "Site reachable. Widget for this tenant not found yet.",
      },
    });
    render(<WebsiteConnectPage />);
    expect(await screen.findByLabelText("Site address")).toHaveValue(
      "https://salon.example",
    );
    expect(screen.getByTestId("connect-status-reason")).toHaveTextContent(
      "Widget for this tenant not found yet.",
    );
  });
});
