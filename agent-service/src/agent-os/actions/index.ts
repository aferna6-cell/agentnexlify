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
  setToolPorts,
  getToolPorts,
  hasToolPorts,
  resetToolPorts,
  type CustomerNoteRecord,
  type CustomerNotesPort,
  type GmailPort,
  type ToolPorts,
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
export { sanitize, sanitizeRecord, REDACTED } from "./sanitize.ts";
