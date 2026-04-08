import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { request, ApiError, BASE } from "./_client";

// Mock fetch globally
const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn();
  vi.useFakeTimers();
  // Mock window.location
  vi.stubGlobal("window", {
    location: {
      href: "http://localhost:3001/dashboard",
      pathname: "/dashboard",
    },
  });
  localStorage.clear();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("request", () => {
  it("makes a GET request with correct headers", async () => {
    const mockData = { id: 1, name: "Test" };
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: () => Promise.resolve(JSON.stringify(mockData)),
    });

    const result = await request("/api/v1/leads");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${BASE}/api/v1/leads`,
      expect.objectContaining({
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }),
    );
    expect(result).toEqual(mockData);
  });

  it("includes Authorization header when token is provided", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: () => Promise.resolve("{}"),
    });

    const result = await request("/api/v1/leads", { token: "test-jwt-token" });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-jwt-token",
        },
      }),
    );
    expect(result).toEqual({});
  });

  it("serializes POST body as JSON", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      text: () => Promise.resolve('{"id":"123"}'),
    });

    const result = await request("/api/v1/leads", {
      method: "POST",
      body: { name: "John", email: "john@example.com" },
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "John", email: "john@example.com" }),
      }),
    );
    expect(result).toEqual({ id: "123" });
  });

  it("returns null for 204 No Content", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const result = await request("/api/v1/leads/123", { method: "DELETE" });

    expect(result).toBeNull();
  });

  it("returns null for empty 200 response", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: () => Promise.resolve(""),
    });

    const result = await request("/api/v1/some-endpoint");

    expect(result).toBeNull();
  });

  it("throws ApiError with detail on non-2xx response", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ detail: "Invalid email" }),
    });

    await expect(request("/api/v1/leads", { method: "POST", body: {} })).rejects.toThrow(
      "Invalid email",
    );
  });

  it("preserves request id and text fallback on non-json API errors", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      text: () => Promise.resolve("temporarily unavailable"),
      headers: new Headers({ "x-request-id": "req-123" }),
    });
    vi.spyOn(console, "error").mockImplementation(() => {});

    await expect(request("/api/v1/leads")).rejects.toMatchObject({
      status: 503,
      message: "temporarily unavailable",
      requestId: "req-123",
    });
  });

  it("normalizes network failures", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    globalThis.fetch.mockRejectedValueOnce(new Error("offline"));

    await expect(request("/api/v1/leads")).rejects.toMatchObject({
      status: 0,
      message: "Network error. Check your connection and try again.",
    });
  });

  it("clears token and redirects on 401", async () => {
    localStorage.setItem("anx_token", "old-token");
    localStorage.setItem("anx_tenant_id", "tenant-123");

    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Invalid token" }),
    });

    await expect(request("/api/v1/leads")).rejects.toThrow("Invalid token");

    expect(localStorage.getItem("anx_token")).toBeNull();
    expect(localStorage.getItem("anx_tenant_id")).toBeNull();
    expect(window.location.href).toBe("/login?expired=1");
  });

  it("does NOT redirect on 401 if already on login page", async () => {
    window.location.pathname = "/login";
    const originalHref = window.location.href;

    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Invalid token" }),
    });

    await expect(request("/api/v1/leads")).rejects.toThrow();

    // href should remain unchanged (no redirect)
    expect(window.location.href).toBe(originalHref);
  });
});

describe("ApiError", () => {
  it("captures status and detail", () => {
    const err = new ApiError(422, { detail: "Email is required" });

    expect(err.status).toBe(422);
    expect(err.message).toBe("Email is required");
    expect(err.body).toEqual({ detail: "Email is required" });
  });

  it("falls back to generic message when detail is missing", () => {
    const err = new ApiError(500, {});

    expect(err.message).toBe("API error 500");
  });

  it("formats FastAPI validation details", () => {
    const err = new ApiError(422, {
      detail: [{ loc: ["body", "email"], msg: "value is not a valid email" }],
    });

    expect(err.message).toBe("body.email: value is not a valid email");
  });
});
