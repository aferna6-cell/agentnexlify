/**
 * Explicit communication-action capability / policy.
 *
 * Workstream C: do not silently enable five-department email. A department
 * may *propose* `send_email` only when every gate below is true:
 *
 *   1. SEND_EMAIL_ENABLED is on (default OFF — production must stay off)
 *   2. the department is in the send-proposal allow-list
 *   3. the ask authorizes an act (not draft/clarify)
 *   4. policy still parks the row at L2 pending_approval
 *
 * Execution stays claim-before-execute, tenant-scoped, and fail-closed in
 * the Python data plane. This file never sends mail.
 *
 * Who may legitimately *propose* a 1:1 customer send (once the flag is on):
 *   - sales            — quote follow-up, outreach to a named recipient
 *   - customer_service — inbound reply to a named customer
 *   - operations       — appointment / "ready for pickup" notice
 *   - invoicing        — invoice / past-due reminder to a named recipient
 *
 * Who must not propose `send_email` in this milestone:
 *   - marketing        — campaigns/blasts are a different risk class
 *   - accounting       — reports, not outbound customer mail
 *   - admin_records    — notes/documents, not mail
 *   - people           — HR memos, not customer mail
 *
 * Default allow-list is Sales only, matching the #700 production contract.
 * Widening the list is an explicit env change, not a silent default.
 */

/** Local flag read — agents must not import action-layer symbols except the executor. */
const SEND_EMAIL_FLAG = "SEND_EMAIL_ENABLED";
const TRUTHY = new Set(["1", "true", "yes", "on"]);

function sendEmailEnabled(): boolean {
  const raw = (process.env[SEND_EMAIL_FLAG] ?? "0").trim().toLowerCase();
  return TRUTHY.has(raw);
}

/** Departments that write 1:1 customer messages and may later be allow-listed. */
export const COMMUNICATION_ELIGIBLE_DEPARTMENTS = [
  "sales",
  "customer_service",
  "operations",
  "invoicing",
] as const;

export type CommunicationEligibleDepartment =
  (typeof COMMUNICATION_ELIGIBLE_DEPARTMENTS)[number];

/** Production default: Sales only. Not five departments. */
export const SEND_EMAIL_PROPOSE_DEPARTMENTS_DEFAULT = ["sales"] as const;

export const SEND_EMAIL_PROPOSE_DEPARTMENTS_FLAG =
  "SEND_EMAIL_PROPOSE_DEPARTMENTS";

export function sendEmailProposeDepartments(): string[] {
  const raw = process.env[SEND_EMAIL_PROPOSE_DEPARTMENTS_FLAG];
  if (raw === undefined || raw.trim() === "") {
    return [...SEND_EMAIL_PROPOSE_DEPARTMENTS_DEFAULT];
  }
  return [
    ...new Set(
      raw
        .split(",")
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean),
    ),
  ];
}

export function isCommunicationEligible(
  departmentId: string | undefined,
): boolean {
  return (COMMUNICATION_ELIGIBLE_DEPARTMENTS as readonly string[]).includes(
    departmentId ?? "",
  );
}

/**
 * True only when this department may create a send_email proposal.
 * The flag being off denies every department, including Sales.
 */
export function canProposeSendEmail(departmentId: string | undefined): boolean {
  if (!departmentId) return false;
  if (!sendEmailEnabled()) return false;
  if (!isCommunicationEligible(departmentId)) return false;
  return sendEmailProposeDepartments().includes(departmentId);
}
