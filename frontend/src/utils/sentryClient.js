const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
const PHONE = /(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)/g;
const KEY_MATERIAL =
  /(?:bearer\s+[A-Za-z0-9._-]{6,}|sk-[A-Za-z0-9_-]{8,}|\b(?:api[_-]?key|token|secret|password|authorization)\s*[=:]\s*\S+)/gi;
const SECRET_KEYS = new Set([
  "authorization",
  "cookie",
  "set-cookie",
  "api_key",
  "apikey",
  "token",
  "access_token",
  "refresh_token",
  "password",
  "secret",
  "dsn",
  "sentry_dsn",
]);

function isSecretKey(key) {
  const normalized = String(key).toLowerCase().replace(/-/g, "_");
  if (
    SECRET_KEYS.has(normalized) ||
    SECRET_KEYS.has(String(key).toLowerCase())
  ) {
    return true;
  }
  return (
    normalized.endsWith("_key") ||
    normalized.endsWith("_token") ||
    normalized.endsWith("_secret") ||
    normalized.includes("password")
  );
}

export function redactText(value) {
  return String(value)
    .replace(EMAIL, "[redacted-email]")
    .replace(PHONE, "[redacted-phone]")
    .replace(KEY_MATERIAL, "[redacted-key]");
}

export function scrubSentryValue(value) {
  if (typeof value === "string") return redactText(value);
  if (Array.isArray(value)) return value.map(scrubSentryValue);
  if (value && typeof value === "object") {
    const cleaned = {};
    for (const [key, item] of Object.entries(value)) {
      cleaned[key] = isSecretKey(key) ? "[redacted]" : scrubSentryValue(item);
    }
    return cleaned;
  }
  return value;
}

export function scrubSentryEvent(event) {
  if (!event || typeof event !== "object") return event;
  const cleaned = scrubSentryValue(event);
  if (cleaned.request) {
    delete cleaned.request.cookies;
    delete cleaned.request.data;
  }
  return cleaned;
}

export function scrubSentryBreadcrumb(crumb) {
  if (!crumb || typeof crumb !== "object") return null;
  return scrubSentryValue(crumb);
}

/**
 * Start Sentry when a DSN is present. An empty DSN does not call init.
 * tracesSampleRate matches the backend hardcode (0.1); it is not an env var.
 */
export function startSentry(Sentry, dsn) {
  const cleaned = (dsn || "").trim();
  if (!cleaned || !Sentry?.init) return false;
  Sentry.init({
    dsn: cleaned,
    sendDefaultPii: false,
    tracesSampleRate: 0.1,
    beforeSend: scrubSentryEvent,
    beforeBreadcrumb: scrubSentryBreadcrumb,
  });
  globalThis.Sentry = Sentry;
  return true;
}

export function initFrontendSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!(dsn || "").trim()) return false;
  import("@sentry/react")
    .then((mod) => {
      startSentry(mod, dsn);
    })
    .catch(() => {
      console.error("Frontend Sentry failed to load");
    });
  return true;
}
