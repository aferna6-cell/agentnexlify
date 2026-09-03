/**
 * Action layer — public surface.
 *
 * Agents and hosts import from here. The rule the whole layer exists to enforce:
 * call `executeAction()`, never a tool's own `execute()`.
 */

export * from "./types.ts";
export { defineTool, type ToolSpec } from "./define-tool.ts";
export {
  ToolRegistry,
  toolRegistry,
  describeTool,
  type AnyTool,
} from "./registry.ts";
export {
  evaluateActionPolicy,
  loadToolPolicy,
  setToolPolicyProvider,
  hasToolPolicyProvider,
  resetToolPolicyProvider,
  DEFAULT_APPROVAL_THRESHOLD,
  DEFAULT_TOOL_POLICY,
  type PolicyDecision,
  type PolicyEvaluation,
  type PolicyTool,
  type TenantToolPolicy,
  type ToolPolicyProvider,
} from "./policy.ts";
export {
  InMemoryActionStore,
  setActionStore,
  getActionStore,
  hasActionStore,
  resetActionStore,
  type ActionStore,
  type ActionExecutionFilter,
} from "./store.ts";
export {
  InMemoryCustomerNotesPort,
  InMemoryCalendarPort,
  InMemoryCrmPort,
  InMemoryInvoicePort,
  CANONICAL_LEAD_STATUSES,
  setToolPorts,
  getToolPorts,
  hasToolPorts,
  resetToolPorts,
  type CustomerNoteRecord,
  type CustomerNotesPort,
  type CalendarPort,
  type CrmPort,
  type InvoicePort,
  type ToolPorts,
  type CalendarEventRecord,
  type CustomerRecord,
  type InvoiceRecord,
} from "./ports.ts";
export {
  executeAction,
  approveAction,
  rejectAction,
  getActionExecution,
  ActionNotFoundError,
  ActionStateError,
  type ActionOutcome,
  type ApproveActionInput,
  type ExecuteActionInput,
  type RejectActionInput,
} from "./executor.ts";
export { getBusinessProfile } from "./tools/get_business_profile.ts";
export { addCustomerNote } from "./tools/add_customer_note.ts";
export { sendEmail } from "./tools/send_email.ts";
export { getCalendarAvailability } from "./tools/get_calendar_availability.ts";
export { createCalendarEvent } from "./tools/create_calendar_event.ts";
export { rescheduleCalendarEvent } from "./tools/reschedule_calendar_event.ts";
export { cancelCalendarEvent } from "./tools/cancel_calendar_event.ts";
export { getCustomer } from "./tools/get_customer.ts";
export { searchCustomers } from "./tools/search_customers.ts";
export { updateCustomer } from "./tools/update_customer.ts";
export { createCustomer } from "./tools/create_customer.ts";
export { updateLeadStage } from "./tools/update_lead_stage.ts";
export { listOverdueInvoices } from "./tools/list_overdue_invoices.ts";
export { getInvoice } from "./tools/get_invoice.ts";
export { createInvoiceDraft } from "./tools/create_invoice_draft.ts";
export { sendInvoice } from "./tools/send_invoice.ts";
export { sendInvoiceReminder } from "./tools/send_invoice_reminder.ts";
export {
  sendEmailEnabled,
  SEND_EMAIL_FLAG,
  SEND_EMAIL_TOOL_ID,
  calendarActionsEnabled,
  crmActionsEnabled,
  invoiceActionsEnabled,
  CALENDAR_ACTIONS_FLAG,
  CRM_ACTIONS_FLAG,
  INVOICE_ACTIONS_FLAG,
  CALENDAR_TOOL_IDS,
  CRM_TOOL_IDS,
  INVOICE_TOOL_IDS,
} from "./flags.ts";
export { sanitize, sanitizeRecord, REDACTED } from "./sanitize.ts";
