/**
 * Explicit department capabilities for external communication tools.
 *
 * Routing does not grant permission. A department may propose a tool only when
 * this table grants the capability, and policy still applies the feature flag,
 * risk level, tenant restrictions, and per-action owner approval.
 */

export const SEND_EMAIL_CAPABLE_DEPARTMENTS = [
  "sales",
  "marketing",
  "customer_service",
  "operations",
  "invoicing",
] as const;

const sendEmailDepartments = new Set<string>(SEND_EMAIL_CAPABLE_DEPARTMENTS);

export function canProposeSendEmail(agentId: string | undefined): boolean {
  return Boolean(agentId && sendEmailDepartments.has(agentId));
}
