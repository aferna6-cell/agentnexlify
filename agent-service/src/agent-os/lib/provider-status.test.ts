import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeApiKey,
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

test("readAiLiveStatus reports invalid_api_key without putting the key in the URL", async () => {
  resetProviderStatusForTests();
  const previous = process.env.ANTHROPIC_API_KEY;
  process.env.ANTHROPIC_API_KEY = '"sk-ant-test-key"';
  const seen: { url?: string; header?: string } = {};
  try {
    const live = await readAiLiveStatus(async (url, init) => {
      seen.url = String(url);
      const headers = new Headers(init?.headers);
      seen.header = headers.get("x-api-key") ?? "";
      return new Response(
        JSON.stringify({
          type: "error",
          error: { type: "authentication_error", message: "invalid x-api-key" },
        }),
        { status: 401 },
      );
    });
    assert.equal(live.ai_live_ok, false);
    assert.equal(live.ai_live_reason, "invalid_api_key");
    assert.equal(seen.url?.includes("sk-ant"), false);
    assert.equal(seen.header, "sk-ant-test-key");
    assert.equal(JSON.stringify(live).includes("sk-ant"), false);
  } finally {
    if (previous === undefined) delete process.env.ANTHROPIC_API_KEY;
    else process.env.ANTHROPIC_API_KEY = previous;
    resetProviderStatusForTests();
  }
});

test("readAiLiveStatus is no_api_key when the env var is empty", async () => {
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
    assert.deepEqual(live, { ai_live_ok: false, ai_live_reason: "no_api_key" });
  } finally {
    if (previous === undefined) delete process.env.ANTHROPIC_API_KEY;
    else process.env.ANTHROPIC_API_KEY = previous;
    resetProviderStatusForTests();
  }
});
