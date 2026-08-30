/**
 * update_customer — Milestone 8 level-1 CRM field update.
 * Explicit field-level input only; unspecified fields are preserved.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_INTERNAL_MUTATION, ToolExecutionError } from "../types.ts";

const Fields = z
  .object({
    phone: z.string().min(1).max(40).optional(),
    email: z.string().email().optional(),
    address: z.string().min(1).max(500).optional(),
    name: z.string().min(1).max(200).optional(),
    subject: z.string().min(1).max(500).optional(),
    metadata: z.record(z.string(), z.string().max(500)).optional(),
  })
  .refine(
    (f) =>
      f.phone !== undefined ||
      f.email !== undefined ||
      f.address !== undefined ||
      f.name !== undefined ||
      f.subject !== undefined ||
      (f.metadata !== undefined && Object.keys(f.metadata).length > 0),
    { message: "at least one field must be provided" },
  );

const Input = z.object({
  customer_id: z.string().min(1),
  fields: Fields,
});

const Output = z.object({
  customerId: z.string(),
  name: z.string(),
  status: z.string(),
  email: z.string().optional(),
  phone: z.string().optional(),
  address: z.string().optional(),
  subject: z.string().optional(),
  updatedFields: z.array(z.string()),
  durable: z.boolean(),
});

export type UpdateCustomerInput = z.infer<typeof Input>;
export type UpdateCustomerOutput = z.infer<typeof Output>;

async function ensureCustomerWritable(
  context: {
    accountId: string;
    ports: { crm: import("../ports.ts").CrmPort };
    sharedContext: import("../../types/agent.ts").SharedContext;
  },
  customerId: string,
): Promise<void> {
  const existing = await context.ports.crm.getCustomer({
    accountId: context.accountId,
    customerId,
  });
  if (existing) return;

  const lead = context.sharedContext.pipelineLeads.find(
    (l) => l.id === customerId,
  );
  if (!lead) {
    throw new ToolExecutionError(
      "customer_not_found",
      `no customer with id "${customerId}" in this business`,
    );
  }
  await context.ports.crm.createCustomer({
    accountId: context.accountId,
    id: lead.id,
    name: lead.name,
    status: lead.status,
    email: lead.email,
    phone: lead.phone,
    subject: lead.subject,
  });
}

export const updateCustomer = defineTool({
  id: "update_customer",
  displayName: "Update customer",
  description:
    "Updates specific fields on a customer/lead record for this business. Only supplied fields change; others are preserved.",
  department: "admin_records",
  requiredConnectors: [],
  riskLevel: RISK_INTERNAL_MUTATION,
  mutating: true,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<UpdateCustomerOutput> {
    const port = context.ports.crm;
    await ensureCustomerWritable(context, input.customer_id);

    const updated = await port.updateCustomer({
      accountId: context.accountId,
      customerId: input.customer_id,
      fields: input.fields,
    });

    context.declareEffect({ port: port.name, durable: port.durable });

    const updatedFields = Object.keys(input.fields).filter(
      (k) => (input.fields as Record<string, unknown>)[k] !== undefined,
    );

    return {
      customerId: updated.id,
      name: updated.name,
      status: updated.status,
      email: updated.email,
      phone: updated.phone,
      address: updated.address,
      subject: updated.subject,
      updatedFields,
      durable: port.durable,
    };
  },

  async verify({ output, input, context }) {
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
    for (const field of output.updatedFields) {
      if (field === "metadata") continue;
      const expected = (input.fields as Record<string, unknown>)[field];
      const actual = (fetched as unknown as Record<string, unknown>)[field];
      if (expected !== undefined && actual !== expected) {
        return {
          verified: false,
          detail: `customer ${output.customerId} field "${field}" mismatch on read-back`,
          evidence: { expected, actual },
        };
      }
    }
    return {
      verified: true,
      detail: `customer ${output.customerId} fields confirmed on read-back`,
      evidence: { updatedFields: output.updatedFields },
    };
  },
});
