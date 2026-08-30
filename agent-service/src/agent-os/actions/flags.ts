/**
 * Process env flags for the action layer. Defaults are fail-closed.
 *
 * SEND_EMAIL_ENABLED must stay off in production. Tests may flip it on
 * in-process; nothing in deploy config or .env.example turns it on.
 */

export const SEND_EMAIL_FLAG = "SEND_EMAIL_ENABLED";
export const SALES_DEPARTMENT = "sales";
export const SEND_EMAIL_TOOL_ID = "send_email";

const TRUTHY = new Set(["1", "true", "yes", "on"]);

/** Env flag, default OFF unless `defaultOn` is set. Unset is off. */
export function envFlagEnabled(name: string, defaultOn = false): boolean {
  const raw = (process.env[name] ?? (defaultOn ? "1" : "0"))
    .trim()
    .toLowerCase();
  return TRUTHY.has(raw);
}

/** Live send_email execute/propose gate. Default off. */
export function sendEmailEnabled(): boolean {
  return envFlagEnabled(SEND_EMAIL_FLAG, false);
}
