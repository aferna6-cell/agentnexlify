/**
 * get_customer — Milestone 8 level-0 CRM read.
 * Tenant-scoped: only returns a lead that belongs to this SharedContext / CRM port.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_READ_ONLY, ToolExecutionError } from "../types.ts";

const Input = z.object({
  customer_id: z.string().min(1),
});

const Output = z.object({
  customerId: z.string(),
  name: z.string(),
  status: z.string(),
  email: z.string().optional(),
  phone: z.string().optional(),
  address: z.string().optional(),
  subject: z.string().optional(),
  source: z.enum(["pipeline", "crm"]),
});

export type GetCustomerInput = z.infer<typeof Input>;
export type GetCustomerOutput = z.infer<typeof Output>;

export const getCustomer = defineTool({
  id: "get_customer",
  displayName: "Get customer",
  description:
    "Reads one customer/lead record for this business by id. Read-only. Never returns another tenant's customer.",
  department: "admin_records",
  requiredConnectors: [],
  riskLevel: RISK_READ_ONLY,
  mutating: false,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<GetCustomerOutput> {
    const lead = context.sharedContext.pipelineLeads.find(
      (l) => l.id === input.customer_id,
    );
    if (lead) {
      return {
        customerId: lead.id,
        name: lead.name,
        status: lead.status,
        subject: lead.subject,
        email: lead.email,
        phone: lead.phone,
        source: "pipeline",
      };
    }

    const fromCrm = await context.ports.crm.getCustomer({
      accountId: context.accountId,
      customerId: input.customer_id,
    });
    if (!fromCrm) {
      throw new ToolExecutionError(
        "customer_not_found",
        `no customer with id "${input.customer_id}" in this business`,
      );
    }
    return {
      customerId: fromCrm.id,
      name: fromCrm.name,
      status: fromCrm.status,
      email: fromCrm.email,
      phone: fromCrm.phone,
      address: fromCrm.address,
      subject: fromCrm.subject,
      source: "crm",
    };
  },
});
