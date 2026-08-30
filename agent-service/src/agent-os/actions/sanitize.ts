/**
 * Sanitizer for anything the action layer persists.
 *
 * Execution rows are an audit trail, and audit trails get read by support, by
 * admins, and by future us. Nothing secret may land in one. This redacts by key
 * name (the value never has to be recognised) and caps size so one runaway
 * payload cannot bloat the tenant's history.
 */

/**
 * Key names that mark a value as sensitive. Matched against whole tokens, not
 * as substrings: a substring match redacts "businessName" because it contains
 * "ssn", which is how well-meaning redaction quietly destroys an audit trail.
 */
const SECRET_TOKENS = new Set([
  "password",
  "passwd",
  "passphrase",
  "secret",
  "secrets",
  "token",
  "tokens",
  "apikey",
  "credential",
  "credentials",
  "authorization",
  "auth",
  "bearer",
  "signature",
  "cookie",
  "cookies",
  "otp",
  "pin",
  "cvv",
  "ssn",
  "key",
  "keys",
]);

/** Split camelCase / snake_case / kebab-case into lowercase word tokens. */
export function keyTokens(key: string): string[] {
  return key
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

export function isSecretKey(key: string): boolean {
  return keyTokens(key).some((t) => SECRET_TOKENS.has(t));
}

export const REDACTED = "[redacted]";

/** Longest string kept verbatim; longer values are truncated with a marker. */
export const MAX_STRING_LENGTH = 2000;
/** Longest array kept; the remainder is summarized. */
export const MAX_ARRAY_LENGTH = 50;
/** How deep to walk before collapsing to a marker. */
export const MAX_DEPTH = 6;

function truncate(value: string): string {
  if (value.length <= MAX_STRING_LENGTH) return value;
  return `${value.slice(0, MAX_STRING_LENGTH)}…[truncated ${value.length - MAX_STRING_LENGTH} chars]`;
}

function walk(value: unknown, depth: number, shorten: boolean): unknown {
  if (value === null || value === undefined) return value ?? null;
  if (typeof value === "string") return shorten ? truncate(value) : value;
  if (typeof value === "number" || typeof value === "boolean") return value;
  if (typeof value === "bigint") return value.toString();
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "function" || typeof value === "symbol")
    return "[unserializable]";
  if (depth >= MAX_DEPTH) return "[max depth]";

  if (Array.isArray(value)) {
    const kept = value
      .slice(0, MAX_ARRAY_LENGTH)
      .map((v) => walk(v, depth + 1, shorten));
    if (value.length > MAX_ARRAY_LENGTH)
      kept.push(`[+${value.length - MAX_ARRAY_LENGTH} more]`);
    return kept;
  }

  if (typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, v] of Object.entries(value as Record<string, unknown>)) {
      out[key] = isSecretKey(key) ? REDACTED : walk(v, depth + 1, shorten);
    }
    return out;
  }

  return "[unserializable]";
}

/** Redact + bound an arbitrary value for persistence. */
export function sanitize(value: unknown): unknown {
  return walk(value, 0, true);
}

/** Redact validated inputs without shortening bytes executed after approval. */
export function sanitizeRecord(
  value: unknown,
  { shorten = true }: { shorten?: boolean } = {},
): Record<string, unknown> {
  const cleaned = walk(value, 0, shorten);
  if (cleaned && typeof cleaned === "object" && !Array.isArray(cleaned)) {
    return cleaned as Record<string, unknown>;
  }
  return { value: cleaned };
}

/** An error message safe to persist: sanitized, single line, bounded. */
export function sanitizeErrorMessage(message: string): string {
  return truncate(message.replace(/\s+/g, " ").trim()).slice(0, 500);
}
