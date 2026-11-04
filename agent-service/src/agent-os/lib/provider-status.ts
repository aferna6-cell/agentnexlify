/**
 * Sanitized Anthropic liveness. Reason codes only — never the key, request id,
 * or provider body.
 */

export type AiLiveStatus = { ai_live_ok: boolean; ai_live_reason: string };

const REASON_RE = /^[a-z0-9_]{1,40}$/;
const SECRET_RE =
  /sk-ant-[A-Za-z0-9_-]+|(x-api-key|api[_-]?key|authorization|bearer)\s*[:=]\s*\S+/gi;
const TTL_MS = 60_000;

let cached: { at: number; live: AiLiveStatus } | null = null;

export function normalizeApiKey(raw: string | undefined | null): string {
  let key = (raw ?? "").trim();
  if (
    key.length >= 2 &&
    (key[0] === '"' || key[0] === "'") &&
    key[key.length - 1] === key[0]
  ) {
    key = key.slice(1, -1).trim();
  }
  return key;
}

function readStatus(err: unknown): number | null {
  if (!err || typeof err !== "object") return null;
  const record = err as { status?: unknown; statusCode?: unknown };
  if (typeof record.status === "number") return record.status;
  if (typeof record.statusCode === "number") return record.statusCode;
  return null;
}

function blobOf(err: unknown): string {
  if (typeof err === "string") return err;
  if (!err || typeof err !== "object") return "";
  const record = err as {
    name?: unknown;
    message?: unknown;
    error?: { type?: unknown; message?: unknown };
  };
  const nested = record.error;
  return [record.name, nested?.type, nested?.message, record.message]
    .filter((part) => typeof part === "string")
    .join(" ");
}

export function sanitizeProviderReason(err: unknown): string {
  const name =
    err && typeof err === "object" && "name" in err
      ? String((err as { name: unknown }).name)
      : "";
  if (name === "UsageCapExceededError") return "usage_cap_exceeded";
  if (name === "ModelUnavailableError") return "no_api_key";
  const status = readStatus(err);
  const text = blobOf(err).replace(SECRET_RE, "").toLowerCase();
  if (
    status === 401 ||
    text.includes("invalid x-api-key") ||
    text.includes("authentication_error")
  ) {
    return "invalid_api_key";
  }
  if (status === 403 || text.includes("permission_error"))
    return "permission_denied";
  if (
    status === 404 ||
    text.includes("not_found_error") ||
    (text.includes("model") && text.includes("not found"))
  ) {
    return "invalid_model";
  }
  if (status === 429 || text.includes("rate_limit")) return "rate_limited";
  if (
    status === 408 ||
    status === 504 ||
    text.includes("timeout") ||
    text.includes("timed out")
  )
    return "timeout";
  if (status === 529 || status === 503 || text.includes("overloaded"))
    return "overloaded";
  if (status === null && text.trim() === "") return "provider_unreachable";
  return "provider_error";
}

export function noteProviderResult(ok: boolean, reason: string): void {
  const ai_live_reason = ok
    ? "ok"
    : REASON_RE.test(reason)
      ? reason
      : "provider_error";
  cached = { at: Date.now(), live: { ai_live_ok: ok, ai_live_reason } };
}

export function resetProviderStatusForTests(): void {
  cached = null;
}

export async function readAiLiveStatus(
  fetchImpl: typeof fetch = fetch,
): Promise<AiLiveStatus> {
  const key = normalizeApiKey(process.env.ANTHROPIC_API_KEY);
  if (!key) {
    noteProviderResult(false, "no_api_key");
    return { ai_live_ok: false, ai_live_reason: "no_api_key" };
  }
  if (cached && Date.now() - cached.at < TTL_MS) return cached.live;

  try {
    const res = await fetchImpl("https://api.anthropic.com/v1/models?limit=1", {
      method: "GET",
      headers: {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
      },
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      noteProviderResult(true, "ok");
      return cached!.live;
    }
    const text = await res.text().catch(() => "");
    const reason = sanitizeProviderReason({
      status: res.status,
      message: text,
    });
    console.warn(
      `anthropic probe failed reason=${reason} status=${res.status}`,
    );
    noteProviderResult(false, reason);
    return cached!.live;
  } catch (err) {
    const reason = sanitizeProviderReason(err);
    console.warn(`anthropic probe failed reason=${reason}`);
    noteProviderResult(false, reason);
    return cached!.live;
  }
}
