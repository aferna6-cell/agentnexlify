/**
 * Tool registry — the source of truth for which tools exist.
 *
 * Deliberately the same shape as `agents/_registry.ts`: a class that rejects
 * duplicate ids at construction, plus one module-level instance holding the
 * built-in tools. Importing this module validates every tool definition, so a
 * malformed or duplicated tool fails at import time and therefore in CI.
 *
 * Adding a tool is one file plus one line here — see
 * docs/agent-os-action-layer.md.
 */

import type { TenantToolPolicy } from "./policy.ts";
import {
  RISK_LABELS,
  type ErasedTool,
  type RiskLevel,
  type ToolDefinition,
  type ToolMetadata,
} from "./types.ts";
import { getBusinessProfile } from "./tools/get_business_profile.ts";
import { addCustomerNote } from "./tools/add_customer_note.ts";
import { sendEmail } from "./tools/send_email.ts";
import { getCalendarAvailability } from "./tools/get_calendar_availability.ts";
import { createCalendarEvent } from "./tools/create_calendar_event.ts";
import { rescheduleCalendarEvent } from "./tools/reschedule_calendar_event.ts";
import { cancelCalendarEvent } from "./tools/cancel_calendar_event.ts";
import { getCustomer } from "./tools/get_customer.ts";
import { searchCustomers } from "./tools/search_customers.ts";
import { updateCustomer } from "./tools/update_customer.ts";
import { createCustomer } from "./tools/create_customer.ts";
import { updateLeadStage } from "./tools/update_lead_stage.ts";
import { listOverdueInvoices } from "./tools/list_overdue_invoices.ts";
import { getInvoice } from "./tools/get_invoice.ts";
import { createInvoiceDraft } from "./tools/create_invoice_draft.ts";
import { sendInvoice } from "./tools/send_invoice.ts";
import { sendInvoiceReminder } from "./tools/send_invoice_reminder.ts";

export type AnyTool = ErasedTool;

export class ToolRegistry {
  private readonly byId = new Map<string, ErasedTool>();

  constructor(tools: ToolDefinition<never, never>[] | ErasedTool[] = []) {
    for (const tool of tools) this.register(tool as ErasedTool);
  }

  /**
   * Register a tool. Duplicate ids are a programming error, never a warning.
   *
   * This is the single place a tool's generic types are erased: the registry
   * holds every tool at once, so it cannot hold their concrete types. The cast
   * is sound because `defineTool` already validated the definition and because
   * the executor re-validates every input and output through the tool's own
   * schemas before and after it runs.
   */
  register<TInput, TOutput>(
    tool: ToolDefinition<TInput, TOutput> | ErasedTool,
  ): void {
    if (this.byId.has(tool.id)) {
      throw new Error(`duplicate tool id "${tool.id}"`);
    }
    this.byId.set(tool.id, tool as unknown as ErasedTool);
  }

  has(id: string): boolean {
    return this.byId.has(id);
  }

  /** Fetch a tool, or null. The executor turns null into an audited denial. */
  find(id: string): ErasedTool | null {
    return this.byId.get(id) ?? null;
  }

  /** Fetch a tool, throwing when it does not exist. */
  get(id: string): ErasedTool {
    const tool = this.byId.get(id);
    if (!tool) throw new Error(`unknown tool id "${id}"`);
    return tool;
  }

  all(): ErasedTool[] {
    return [...this.byId.values()];
  }

  byDepartment(department: string): ErasedTool[] {
    return this.all().filter((t) => t.department === department);
  }

  byRiskLevel(level: RiskLevel): ErasedTool[] {
    return this.all().filter((t) => t.riskLevel === level);
  }

  /** What an agent or the orchestrator may see without executing anything. */
  metadata(): ToolMetadata[] {
    return this.all().map(describeTool);
  }

  /**
   * Tools this tenant may use, honoring its allow/deny lists. This is the hook
   * per-business integrations plug into: a tenant with no Gmail connector simply
   * does not see the Gmail tool.
   */
  availableFor(policy: TenantToolPolicy | undefined): ErasedTool[] {
    const p = policy ?? {};
    return this.all()
      .filter((t) =>
        p.enabledToolIds ? p.enabledToolIds.includes(t.id) : true,
      )
      .filter((t) => !(p.disabledToolIds ?? []).includes(t.id));
  }

  /** Test hook: a registry holding only the given tools. */
  static of(tools: ErasedTool[]): ToolRegistry {
    return new ToolRegistry(tools);
  }
}

export function describeTool(
  tool: ErasedTool | ToolDefinition<never, never>,
): ToolMetadata {
  return {
    id: tool.id,
    displayName: tool.displayName,
    description: tool.description,
    department: tool.department,
    requiredConnectors: tool.requiredConnectors,
    riskLevel: tool.riskLevel,
    riskLabel: RISK_LABELS[tool.riskLevel],
    mutating: tool.mutating,
    requiresApproval: tool.requiresApproval,
    verifiable: typeof tool.verify === "function",
  };
}

/** The built-in tools. */
export const toolRegistry = new ToolRegistry();
toolRegistry.register(getBusinessProfile);
toolRegistry.register(addCustomerNote);
toolRegistry.register(sendEmail);
toolRegistry.register(getCalendarAvailability);
toolRegistry.register(createCalendarEvent);
toolRegistry.register(rescheduleCalendarEvent);
toolRegistry.register(cancelCalendarEvent);
toolRegistry.register(getCustomer);
toolRegistry.register(searchCustomers);
toolRegistry.register(updateCustomer);
toolRegistry.register(createCustomer);
toolRegistry.register(updateLeadStage);
toolRegistry.register(listOverdueInvoices);
toolRegistry.register(getInvoice);
toolRegistry.register(createInvoiceDraft);
toolRegistry.register(sendInvoice);
toolRegistry.register(sendInvoiceReminder);
