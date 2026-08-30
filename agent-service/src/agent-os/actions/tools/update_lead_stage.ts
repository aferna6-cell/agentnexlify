/**
 * update_lead_stage — Milestone 8 level-1 pipeline transition.
 * Validates against tenant pipeline_stages or the canonical closed set.
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_INTERNAL_MUTATION, ToolExecutionError } from "../types.ts";
import { CANONICAL_LEAD_STATUSES } from "../ports.ts";

const Input = z.object({
  customer_id: z.string().min(1),
  status: z.string().min(1).max(80),
});

const Output = z.object({
  customerId: z.string(),
  name: z.string(),
  previousStatus: z.string(),
  status: z.string(),
  durable: z.boolean(),
});

export type UpdateLeadStageInput = z.infer<typeof Input>;
export type UpdateLeadStageOutput = z.infer<typeof Output>;

function allowedStatuses(context: {
  sharedContext: {
    pipelineStages?: string[];
    pipelineLeads: { status: string }[];
  };
}): Set<string> {
  const stages = context.sharedContext.pipelineStages;
  if (stages && stages.length > 0) {
    return new Set(stages.map((s) => s.trim().toLowerCase()).filter(Boolean));
  }
  return new Set(CANONICAL_LEAD_STATUSES.map((s) => s.toLowerCase()));
}

export const updateLeadStage = defineTool({
  id: "update_lead_stage",
  displayName: "Update lead stage",
  description:
    "Moves a lead to a validated pipeline status for this business. Free-text invalid stages are rejected.",
  department: "admin_records",
  requiredConnectors: [],
  riskLevel: RISK_INTERNAL_MUTATION,
  mutating: true,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<UpdateLeadStageOutput> {
    const status = input.status.trim().toLowerCase();
    const allowed = allowedStatuses(context);
    if (!allowed.has(status)) {
      throw new ToolExecutionError(
        "invalid_lead_stage",
        `status "${input.status}" is not a valid pipeline stage for this business`,
      );
    }

    const port = context.ports.crm;
    let before = await port.getCustomer({
      accountId: context.accountId,
      customerId: input.customer_id,
    });
    if (!before) {
      const lead = context.sharedContext.pipelineLeads.find(
        (l) => l.id === input.customer_id,
      );
      if (!lead) {
        throw new ToolExecutionError(
          "customer_not_found",
          `no customer with id "${input.customer_id}" in this business`,
        );
      }
      before = await port.createCustomer({
        accountId: context.accountId,
        id: lead.id,
        name: lead.name,
        status: lead.status,
        email: lead.email,
        phone: lead.phone,
        subject: lead.subject,
      });
    }

    const previousStatus = before.status;
    const updated = await port.updateLeadStage({
      accountId: context.accountId,
      customerId: input.customer_id,
      status,
    });

    context.declareEffect({ port: port.name, durable: port.durable });

    return {
      customerId: updated.id,
      name: updated.name,
      previousStatus,
      status: updated.status,
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
    if (fetched.status !== output.status) {
      return {
        verified: false,
        detail: `lead stage mismatch on read-back (expected ${output.status}, got ${fetched.status})`,
      };
    }
    return {
      verified: true,
      detail: `lead ${output.customerId} stage confirmed as ${output.status}`,
      evidence: {
        previousStatus: output.previousStatus,
        status: fetched.status,
      },
    };
  },
});
