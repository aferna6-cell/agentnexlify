/**
 * search_customers — Milestone 8 level-0 CRM search.
 *
 * Outcomes: exact | unique | multiple | none. Never silently picks among
 * multiple matches (e.g. two Mikes).
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_READ_ONLY } from "../types.ts";
import { resolveByName } from "../../agents/_resolve.ts";

const Match = z.object({
  customerId: z.string(),
  name: z.string(),
  status: z.string().optional(),
});

const Input = z.object({
  query: z.string().min(1).max(200),
});

const Output = z.object({
  kind: z.enum(["exact", "unique", "multiple", "none"]),
  match: Match.optional(),
  matches: z.array(Match).optional(),
  query: z.string(),
});

export type SearchCustomersInput = z.infer<typeof Input>;
export type SearchCustomersOutput = z.infer<typeof Output>;

export const searchCustomers = defineTool({
  id: "search_customers",
  displayName: "Search customers",
  description:
    "Finds customers/leads by name for this business. Returns exact, unique, multiple, or none — never guesses between ambiguous matches.",
  department: "admin_records",
  requiredConnectors: [],
  riskLevel: RISK_READ_ONLY,
  mutating: false,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,

  async execute({ input, context }): Promise<SearchCustomersOutput> {
    const fromPipeline = context.sharedContext.pipelineLeads.map((l) => ({
      customerId: l.id,
      name: l.name,
      status: l.status,
    }));
    const fromCrm = (
      await context.ports.crm.listCustomers({
        accountId: context.accountId,
      })
    ).map((c) => ({
      customerId: c.id,
      name: c.name,
      status: c.status,
    }));

    // Dedupe by id (pipeline wins for display fields already present).
    const byId = new Map<
      string,
      { customerId: string; name: string; status?: string }
    >();
    for (const c of fromCrm) byId.set(c.customerId, c);
    for (const c of fromPipeline) byId.set(c.customerId, c);
    const pool = [...byId.values()];

    const resolution = resolveByName(pool, (c) => c.name, input.query);
    if (resolution.kind === "exact" || resolution.kind === "unique") {
      return {
        kind: resolution.kind,
        match: resolution.match,
        query: input.query,
      };
    }
    if (resolution.kind === "multiple") {
      return {
        kind: "multiple",
        matches: resolution.matches,
        query: input.query,
      };
    }
    return { kind: "none", query: input.query };
  },
});
