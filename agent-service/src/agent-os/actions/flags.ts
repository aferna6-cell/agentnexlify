/**
 * Process env flags for the action layer. Defaults are fail-closed.
 *
 * SEND_EMAIL_ENABLED must stay off in production. Tests may flip it on
 * in-process; nothing in deploy config or .env.example turns it on.
 */

export const SEND_EMAIL_FLAG = "SEND_EMAIL_ENABLED";
export const SALES_DEPARTMENT = "sales";
export const SEND_EMAIL_TOOL_ID = "send_email";

/**
 * Departments that may *propose* send_email when the flag is on.
 *
 * This is capability configuration, not a routing score. Sales is the only
 * department enabled in this milestone. Operations, Customer Service,
 * Invoicing, and Marketing are legitimate future candidates for 1:1
 * operational / reply / collections mail — widening the list is a product
 * decision and does not loosen policy, approval, or the flag default.
 */
export const SEND_EMAIL_PROPOSE_DEPARTMENTS: readonly string[] = [
  SALES_DEPARTMENT,
];

/** Departments that could later propose communication, but are not enabled. */
export const SEND_EMAIL_CANDIDATE_DEPARTMENTS: readonly string[] = [
  "operations",
  "customer_service",
  "invoicing",
  "marketing",
];

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

/**
 * Can this department propose a send? Same rule policy enforces.
 * Flag-off or a department outside SEND_EMAIL_PROPOSE_DEPARTMENTS is false.
 */
export function canProposeSendEmail(departmentId: string | undefined): boolean {
  return (
    sendEmailEnabled() &&
    Boolean(departmentId) &&
    SEND_EMAIL_PROPOSE_DEPARTMENTS.includes(departmentId)
  );
}
