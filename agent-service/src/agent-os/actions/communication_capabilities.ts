/**
 * Department communication capabilities — who may propose vs who may execute.
 *
 * Proposal: departments that legitimately compose customer-facing email may call
 * `resolveEmailSendFromOutput` after drafting. That creates a level-2
 * `send_email` execution row (parked or policy-denied when SEND_EMAIL_ENABLED
 * is off).
 *
 * Execution: when SEND_EMAIL_ENABLED is on, only Sales may pass policy and
 * reach pending_approval. Other departments' proposals are denied at policy
 * with an audit row — they do not silently draft instead.
 *
 * SEND_EMAIL_ENABLED defaults OFF. No production flag change here.
 */

/** Departments that may propose send_email after composing customer email. */
export const EMAIL_PROPOSAL_DEPARTMENTS = new Set([
  "sales",
  "customer_service",
  "marketing",
  "operations",
  "invoicing",
]);

/** Department allowed to execute send_email when SEND_EMAIL_ENABLED is on. */
export const EMAIL_EXECUTION_DEPARTMENT = "sales";

export function mayProposeEmailSend(departmentId: string): boolean {
  return EMAIL_PROPOSAL_DEPARTMENTS.has(departmentId);
}

export function mayExecuteEmailSend(departmentId: string): boolean {
  return departmentId === EMAIL_EXECUTION_DEPARTMENT;
}
