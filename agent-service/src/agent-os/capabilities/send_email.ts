/**
 * Send-email capability configuration.
 *
 * Lives outside the action layer so department resolvers can ask "may I
 * propose a send?" without importing executor/policy/flags. Policy still
 * re-checks the same rule; this is not an execute path.
 *
 * SEND_EMAIL_ENABLED stays default OFF. Widening PROPOSE_DEPARTMENTS is a
 * product decision and does not loosen approval, tenant scope, or the flag.
 */

export const SEND_EMAIL_FLAG = "SEND_EMAIL_ENABLED";
export const SALES_DEPARTMENT = "sales";
export const SEND_EMAIL_TOOL_ID = "send_email";

/**
 * Departments that may *propose* send_email when the flag is on.
 * Sales only in this milestone.
 */
export const SEND_EMAIL_PROPOSE_DEPARTMENTS: readonly string[] = [
  SALES_DEPARTMENT,
];

/** Legitimate later candidates — not enabled. */
export const SEND_EMAIL_CANDIDATE_DEPARTMENTS: readonly string[] = [
  "operations",
  "customer_service",
  "invoicing",
  "marketing",
];

const TRUTHY = new Set(["1", "true", "yes", "on"]);

export function envFlagEnabled(name: string, defaultOn = false): boolean {
  const raw = (process.env[name] ?? (defaultOn ? "1" : "0"))
    .trim()
    .toLowerCase();
  return TRUTHY.has(raw);
}

export function sendEmailEnabled(): boolean {
  return envFlagEnabled(SEND_EMAIL_FLAG, false);
}

export function canProposeSendEmail(departmentId: string | undefined): boolean {
  return (
    sendEmailEnabled() &&
    departmentId !== undefined &&
    SEND_EMAIL_PROPOSE_DEPARTMENTS.includes(departmentId)
  );
}
