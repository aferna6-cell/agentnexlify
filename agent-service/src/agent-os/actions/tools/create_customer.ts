/**
 * create_customer — Milestone 8 level-1. Tenant-scoped and duplicate-aware
 * (email, then phone) before inserting another record.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_INTERNAL_MUTATION, ToolExecutionError } from "../types.ts";

const Input = z.object({
  name: z.string().min(1).max(200),
  email: z.string().email().optional(),
  phone: z.string().min(1).max(40).optional(),
  address: z.string().min(1).max(500).optional(),
  status: z.string().min(1).max(80).optional(),
  subject: z.string().min(1).max(500).optional(),
});

const Output = z.object({
  customerId: z.string(),
  name: z.string(),
  status: z.string(),
  email: z.string().optional(),
  phone: z.string().optional(),
  address: z.string().optional(),
  deduplicated: z.boolean(),
  durable: z.boolean(),
});

export type CreateCustomerToolInput = z.infer<typeof Input>;
export type CreateCustomerToolOutput = z.infer<typeof Output>;

export const createCustomer = defineTool({
  id: "create_customer",
  displayName: "Create customer",
  description:
    "Creates a customer/lead for this business. Checks for an existing email or phone match first and returns that record instead of duplicating.",
  department: "admin_records",
  requiredConnectors: [],
  riskLevel: RISK_INTERNAL_MUTATION,
  mutating: true,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<CreateCustomerToolOutput> {
    if (!input.name.trim()) {
      throw new ToolExecutionError(
        "invalid_input",
        "customer name is required",
      );
    }
    const port = context.ports.crm;
    const before = await port.listCustomers({ accountId: context.accountId });
    const beforeIds = new Set(before.map((c) => c.id));

    const created = await port.createCustomer({
      accountId: context.accountId,
      name: input.name.trim(),
      email: input.email,
      phone: input.phone,
      address: input.address,
      status: input.status ?? "new",
      subject: input.subject,
    });

    const deduplicated = beforeIds.has(created.id);
    context.declareEffect({ port: port.name, durable: port.durable });

    return {
      customerId: created.id,
      name: created.name,
      status: created.status,
      email: created.email,
      phone: created.phone,
      address: created.address,
      deduplicated,
      durable: port.durable,
    };
  },

  async verify({ output, context }) {
    const fetched = await context.ports.crm.getCustomer({
      accountId: context.accountId,
      customerId: output.customerId,
    });
    if (!fetched) {
      return {
        verified: false,
        detail: `customer ${output.customerId} missing on CRM read-back`,
      };
    }
    if (fetched.name !== output.name) {
      return {
        verified: false,
        detail: `customer ${output.customerId} name mismatch on read-back`,
      };
    }
    return {
      verified: true,
      detail: `customer ${output.customerId} confirmed on CRM read-back`,
      evidence: { customerId: fetched.id, deduplicated: output.deduplicated },
    };
  },
});
