import assert from "node:assert/strict";
import test from "node:test";

import {
  AI_LIVE_TTL_MS,
  authedAiLiveBody,
  normalizeApiKey,
  publicHealthBody,
  readAiLiveStatus,
  resetProviderStatusForTests,
  sanitizeProviderReason,
} from "./provider-status.ts";

test("sanitizeProviderReason maps invalid keys and does not echo secrets", () => {
  const secret = "sk-ant-api03-supersecretkeyvalue";
  const reason = sanitizeProviderReason({
    status: 401,
    message: `401 {"type":"error","error":{"type":"authentication_error","message":"invalid x-api-key"},"request_id":"req_secret"} leaked=${secret}`,
  });
  assert.equal(reason, "invalid_api_key");
  assert.equal(reason.includes("sk-ant"), false);
  assert.equal(reason.includes("req_secret"), false);
});

test("sanitizeProviderReason distinguishes model, cap, and missing key", () => {
  assert.equal(
    sanitizeProviderReason({
      status: 404,
      error: { type: "not_found_error", message: "model: claude-retired" },
    }),
    "invalid_model",
  );
  assert.equal(
    sanitizeProviderReason({ name: "UsageCapExceededError", message: "cap" }),
    "usage_cap_exceeded",
  );
  assert.equal(
    sanitizeProviderReason({ name: "ModelUnavailableError" }),
    "no_api_key",
  );
  assert.equal(
    sanitizeProviderReason({ status: 429, message: "rate_limit_error" }),
    "rate_limited",
  );
});

test("normalizeApiKey trims whitespace and wrapping quotes", () => {
  assert.equal(normalizeApiKey('  "sk-ant-example"  '), "sk-ant-example");
  assert.equal(normalizeApiKey(""), "");
  assert.equal(normalizeApiKey(undefined), "");
});

test("public health is only the boolean; the reason stays on the authed body", () => {
  const live = { ai_live: false, ai_live_reason: "invalid_api_key" };
  const pub = publicHealthBody(live);
  assert.deepEqual(pub, { status: "ok", ai_live: false });
  assert.equal("ai_live_reason" in pub, false);
  assert.deepEqual(authedAiLiveBody(live), live);
});

test("readAiLiveStatus sends one cached GET /v1/models and does not complete", async () => {
  resetProviderStatusForTests();
  const previous = process.env.ANTHROPIC_API_KEY;
  process.env.ANTHROPIC_API_KEY = '"sk-ant-test-key"';
  const seen: { url?: string; header?: string; body?: string; calls: number } =
    { calls: 0 };
  try {
    const fetchImpl: typeof fetch = async (url, init) => {
      seen.calls += 1;
      seen.url = String(url);
      const headers = new Headers(init?.headers);
      seen.header = headers.get("x-api-key") ?? "";
      seen.body = String(init?.body ?? "");
      return new Response(
        JSON.stringify({
          type: "error",
          error: { type: "authentication_error", message: "invalid x-api-key" },
        }),
        { status: 401 },
      );
    };
    const first = await readAiLiveStatus(fetchImpl);
    const second = await readAiLiveStatus(fetchImpl);
    assert.equal(first.ai_live, false);
    assert.equal(first.ai_live_reason, "invalid_api_key");
    assert.deepEqual(second, first);
    assert.equal(seen.calls, 1);
    assert.equal(seen.url, "https://api.anthropic.com/v1/models?limit=1");
    assert.equal(seen.header, "sk-ant-test-key");
    assert.equal(seen.body, "");
    assert.equal(JSON.stringify(first).includes("sk-ant"), false);
    assert.ok(AI_LIVE_TTL_MS >= 3 * 60 * 1000);
  } finally {
    if (previous === undefined) delete process.env.ANTHROPIC_API_KEY;
    else process.env.ANTHROPIC_API_KEY = previous;
    resetProviderStatusForTests();
  }
});

test("a present key is not live until GET /v1/models succeeds", async () => {
  resetProviderStatusForTests();
  const previous = process.env.ANTHROPIC_API_KEY;
  process.env.ANTHROPIC_API_KEY = "sk-ant-present";
  try {
    const live = await readAiLiveStatus(async () => {
      return new Response(
        JSON.stringify({ content: [{ type: "text", text: "p" }] }),
        {
          status: 200,
        },
      );
    });
    assert.equal(live.ai_live, true);
    assert.equal(live.ai_live_reason, "ok");
  } finally {
    if (previous === undefined) delete process.env.ANTHROPIC_API_KEY;
    else process.env.ANTHROPIC_API_KEY = previous;
    resetProviderStatusForTests();
  }
});

test("readAiLiveStatus is not live when the env var is empty and does not call", async () => {
  resetProviderStatusForTests();
  const previous = process.env.ANTHROPIC_API_KEY;
  delete process.env.ANTHROPIC_API_KEY;
  try {
    let called = false;
    const live = await readAiLiveStatus(async () => {
      called = true;
      return new Response("ok", { status: 200 });
    });
    assert.equal(called, false);
    assert.deepEqual(live, { ai_live: false, ai_live_reason: "no_api_key" });
  } finally {
    if (previous === undefined) delete process.env.ANTHROPIC_API_KEY;
    else process.env.ANTHROPIC_API_KEY = previous;
    resetProviderStatusForTests();
  }
});
