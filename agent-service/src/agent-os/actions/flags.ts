/**
 * Process env flags for the action layer. Defaults are fail-closed.
 *
 * SEND_EMAIL_ENABLED / RAG_ENABLED / CALENDAR_ACTIONS_ENABLED /
 * CRM_ACTIONS_ENABLED / INVOICE_ACTIONS_ENABLED must stay off in
 * production unless explicitly rolled out.
 */

export const SEND_EMAIL_FLAG = "SEND_EMAIL_ENABLED";
export const SALES_DEPARTMENT = "sales";
export const SEND_EMAIL_TOOL_ID = "send_email";

export const CALENDAR_ACTIONS_FLAG = "CALENDAR_ACTIONS_ENABLED";
export const CRM_ACTIONS_FLAG = "CRM_ACTIONS_ENABLED";
export const INVOICE_ACTIONS_FLAG = "INVOICE_ACTIONS_ENABLED";
export const INVOICING_DEPARTMENT = "invoicing";

/** Calendar tool family — gated by CALENDAR_ACTIONS_ENABLED. */
export const CALENDAR_TOOL_IDS = [
  "get_calendar_availability",
  "create_calendar_event",
  "reschedule_calendar_event",
  "cancel_calendar_event",
] as const;

/** CRM tool family — gated by CRM_ACTIONS_ENABLED (notes stay ungated L1). */
export const CRM_TOOL_IDS = [
  "get_customer",
  "search_customers",
  "update_customer",
  "create_customer",
  "update_lead_stage",
] as const;

/** Invoice tool family — gated by INVOICE_ACTIONS_ENABLED. */
export const INVOICE_TOOL_IDS = [
  "list_overdue_invoices",
  "get_invoice",
  "create_invoice_draft",
  "send_invoice",
  "send_invoice_reminder",
] as const;

export const LIST_OVERDUE_INVOICES_TOOL_ID = "list_overdue_invoices";
export const GET_INVOICE_TOOL_ID = "get_invoice";
export const CREATE_INVOICE_DRAFT_TOOL_ID = "create_invoice_draft";
export const SEND_INVOICE_TOOL_ID = "send_invoice";
export const SEND_INVOICE_REMINDER_TOOL_ID = "send_invoice_reminder";

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

/** Calendar Action Executor tools. Default off. */
export function calendarActionsEnabled(): boolean {
  return envFlagEnabled(CALENDAR_ACTIONS_FLAG, false);
}

/** CRM Action Executor tools (excluding add_customer_note). Default off. */
export function crmActionsEnabled(): boolean {
  return envFlagEnabled(CRM_ACTIONS_FLAG, false);
}

export function isCalendarToolId(id: string): boolean {
  return (CALENDAR_TOOL_IDS as readonly string[]).includes(id);
}

export function isCrmToolId(id: string): boolean {
  return (CRM_TOOL_IDS as readonly string[]).includes(id);
}

/** Invoice Action Executor tools. Default off. */
export function invoiceActionsEnabled(): boolean {
  return envFlagEnabled(INVOICE_ACTIONS_FLAG, false);
}

export function isInvoiceToolId(id: string): boolean {
  return (INVOICE_TOOL_IDS as readonly string[]).includes(id);
}
