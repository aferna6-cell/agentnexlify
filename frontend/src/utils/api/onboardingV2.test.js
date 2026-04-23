import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  autoKb,
  bulkImportFaqs,
  completeWizard,
  getPreset,
  getReadiness,
  getWidgetHealth,
  saveHours,
  saveStep,
  startWizard,
} from "./onboardingV2";

const TOKEN = "test-bearer-token";
const BASE = "/api/v1/onboarding/v2";

function mockOk(data) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  });
}

function mockError(status, detail) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status,
    json: () => Promise.resolve({ detail }),
  });
}

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("startWizard", () => {
  it("POSTs to /start with vertical", async () => {
    mockOk({ session_id: "sess_abc" });
    const result = await startWizard(TOKEN, "plumbing");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${BASE}/start`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ vertical: "plumbing" }),
        headers: expect.objectContaining({ Authorization: `Bearer ${TOKEN}` }),
      }),
    );
    expect(result.session_id).toBe("sess_abc");
  });

  it("throws on non-OK response", async () => {
    mockError(400, "Vertical invalid");
    await expect(startWizard(TOKEN, "bad")).rejects.toThrow("Vertical invalid");
  });
});

describe("saveStep", () => {
  it("POSTs to /step/:num with field updates", async () => {
    mockOk({ saved: true });
    await saveStep(TOKEN, 2, { business_name: "Acme" });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${BASE}/step/2`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ business_name: "Acme" }),
      }),
    );
  });
});

describe("completeWizard", () => {
  it("POSTs to /complete", async () => {
    mockOk({ ready_to_launch: true, widget_api_key: "wk_abc" });
    const result = await completeWizard(TOKEN);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${BASE}/complete`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.ready_to_launch).toBe(true);
  });
});

describe("autoKb", () => {
  it("POSTs to /auto-kb with url and passes signal", async () => {
    mockOk({ faqs_found: 5 });
    const controller = new AbortController();
    await autoKb(TOKEN, "https://example.com", controller.signal);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${BASE}/auto-kb`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ url: "https://example.com" }),
        signal: controller.signal,
      }),
    );
  });
});

describe("getPreset", () => {
  it("fetches preset for a vertical", async () => {
    mockOk({ vertical: "hvac", default_services: ["HVAC Install"] });
    const result = await getPreset(TOKEN, "hvac");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${BASE}/preset/hvac`,
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: `Bearer ${TOKEN}` }),
      }),
    );
    expect(result.vertical).toBe("hvac");
  });
});

describe("getReadiness", () => {
  it("GETs /readiness", async () => {
    mockOk({ ready_to_launch: false, criteria: {} });
    const result = await getReadiness(TOKEN);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${BASE}/readiness`,
      expect.objectContaining({ method: "GET" }),
    );
    expect(result.ready_to_launch).toBe(false);
  });
});

describe("bulkImportFaqs", () => {
  it("POSTs to /faqs/bulk with text", async () => {
    mockOk({ imported: 3 });
    await bulkImportFaqs(TOKEN, "Q1\nA1\nQ2\nA2");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${BASE}/faqs/bulk`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "Q1\nA1\nQ2\nA2" }),
      }),
    );
  });
});

describe("saveHours", () => {
  it("POSTs to /hours with timezone and hours", async () => {
    const hours = { monday: { open: "08:00", close: "17:00" } };
    mockOk({ saved: true });
    await saveHours(TOKEN, "America/New_York", hours);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${BASE}/hours`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ timezone: "America/New_York", hours }),
      }),
    );
  });
});

describe("getWidgetHealth", () => {
  it("GETs /widget/health with encoded domain", async () => {
    mockOk({
      loaded: true,
      reachable: true,
      origin_allowed: true,
      domain: "example.com",
    });
    const result = await getWidgetHealth(TOKEN, "example.com");
    const calledUrl = globalThis.fetch.mock.calls[0][0];
    expect(calledUrl).toContain("domain=example.com");
    expect(calledUrl).toContain("/api/v1/widget/health");
    expect(result.loaded).toBe(true);
  });

  it("URL-encodes special characters in domain", async () => {
    mockOk({
      loaded: false,
      reachable: false,
      origin_allowed: false,
      domain: "sub.example.com",
    });
    await getWidgetHealth(TOKEN, "sub.example.com");
    const calledUrl = globalThis.fetch.mock.calls[0][0];
    expect(calledUrl).toContain("domain=sub.example.com");
  });

  it("throws on error response", async () => {
    mockError(404, "Domain not found");
    await expect(getWidgetHealth(TOKEN, "notfound.com")).rejects.toThrow(
      "Domain not found",
    );
  });
});

describe("error handling", () => {
  it("uses message field as fallback when detail is missing", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ message: "Server error" }),
    });
    await expect(startWizard(TOKEN, "plumbing")).rejects.toThrow(
      "Server error",
    );
  });

  it("uses status code when no error body", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: () => Promise.resolve({}),
    });
    await expect(completeWizard(TOKEN)).rejects.toThrow("Request failed: 503");
  });
});
