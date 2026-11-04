import { describe, expect, it, vi } from "vitest";

import {
  initFrontendSentry,
  scrubSentryBreadcrumb,
  scrubSentryEvent,
  startSentry,
} from "./sentryClient";

describe("frontend Sentry", () => {
  it("does not initialize when the DSN is unset", () => {
    const init = vi.fn();
    expect(startSentry({ init }, "")).toBe(false);
    expect(startSentry({ init }, "   ")).toBe(false);
    expect(init).not.toHaveBeenCalled();
    expect(initFrontendSentry()).toBe(false);
  });

  it("initializes only with a DSN and scrubs breadcrumbs and log entries", () => {
    const init = vi.fn();
    expect(
      startSentry({ init }, "https://public@example.ingest.sentry.io/1"),
    ).toBe(true);
    const options = init.mock.calls[0][0];
    expect(options.sendDefaultPii).toBe(false);
    expect(options.tracesSampleRate).toBe(0.1);
    const event = options.beforeSend({
      breadcrumbs: {
        values: [
          {
            message: "ada@example.com Bearer sk-live-secretvalue",
            data: { api_key: "sk-live-secretvalue", path: "/ok" },
          },
        ],
      },
      logentry: { message: "token=abc123secret ada@example.com" },
    });
    const blob = JSON.stringify(event);
    expect(blob).not.toContain("ada@example.com");
    expect(blob).not.toContain("sk-live-secretvalue");
    expect(blob).not.toContain("abc123secret");
    expect(event.breadcrumbs.values[0].data.api_key).toBe("[redacted]");
    expect(event.breadcrumbs.values[0].data.path).toBe("/ok");
    expect(options.beforeBreadcrumb("nope")).toBeNull();
    expect(
      options.beforeBreadcrumb({
        message: "ada@example.com",
        data: { password: "x" },
      }).data.password,
    ).toBe("[redacted]");
  });

  it("drops a non-object breadcrumb", () => {
    expect(scrubSentryBreadcrumb(null)).toBeNull();
    expect(scrubSentryEvent({ message: "ada@example.com" }).message).toBe(
      "[redacted-email]",
    );
  });
});
