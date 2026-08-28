/**
 * defineTool — the only supported way to create a tool.
 *
 * Mirrors `agents/_schema.ts::defineAgent`: a Zod schema validates the metadata
 * and a handful of cross-field rules are enforced here, so a malformed tool
 * fails at import time (and therefore in CI) rather than at 2am in production.
 *
 * The rules encode the risk model:
 *  - a level-0 tool may not mutate and may not require approval (it is a read),
 *  - anything that mutates is at least level 1,
 *  - level 2 (external communication) and level 3 (financial / legal /
 *    destructive) always declare `requiresApproval: true`. Tenant policy can add
 *    approval requirements; it can never remove one a tool declared.
 *  - only a mutating tool may declare `verify()` — there is nothing to verify
 *    about a read.
 */

import { z } from "zod";
import { RISK_LEVELS, type RiskLevel, type ToolDefinition, type ToolImplementation } from "./types.ts";

const MetaSchema = z.object({
  id: z.string().regex(/^[a-z][a-z0-9_]*$/, "tool id must be snake_case"),
  displayName: z.string().min(1),
  description: z.string().min(1),
  department: z.string().min(1).optional(),
  requiredConnectors: z.array(z.string().min(1)).default([]),
  implementation: z.enum(["engine", "data_plane"]).default("engine"),
  riskLevel: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]),
  mutating: z.boolean(),
  requiresApproval: z.boolean(),
});

/** The author-facing shape: metadata + schemas + behaviour. */
export interface ToolSpec<TInput, TOutput> {
  id: string;
  displayName: string;
  description: string;
  department?: string;
  requiredConnectors?: string[];
  /** Where the body runs. Defaults to "engine". */
  implementation?: ToolImplementation;
  riskLevel: RiskLevel;
  mutating: boolean;
  requiresApproval: boolean;
  inputSchema: z.ZodType<TInput>;
  outputSchema: z.ZodType<TOutput>;
  /** Required for an engine tool; forbidden for a data-plane one. */
  execute?: ToolDefinition<TInput, TOutput>["execute"];
  verify?: ToolDefinition<TInput, TOutput>["verify"];
}

export function defineTool<TInput, TOutput>(spec: ToolSpec<TInput, TOutput>): ToolDefinition<TInput, TOutput> {
  const meta = MetaSchema.parse({
    id: spec.id,
    displayName: spec.displayName,
    description: spec.description,
    department: spec.department,
    requiredConnectors: spec.requiredConnectors ?? [],
    implementation: spec.implementation ?? "engine",
    riskLevel: spec.riskLevel,
    mutating: spec.mutating,
    requiresApproval: spec.requiresApproval,
  });

  if (!RISK_LEVELS.includes(meta.riskLevel as RiskLevel)) {
    throw new Error(`[${meta.id}] riskLevel must be one of ${RISK_LEVELS.join(", ")}`);
  }
  if (meta.riskLevel === 0 && meta.mutating) {
    throw new Error(`[${meta.id}] a level-0 tool is read-only — set riskLevel >= 1 to mutate`);
  }
  if (meta.riskLevel === 0 && meta.requiresApproval) {
    throw new Error(`[${meta.id}] a read-only tool must not require approval`);
  }
  if (meta.mutating && meta.riskLevel === 0) {
    throw new Error(`[${meta.id}] a mutating tool must declare riskLevel >= 1`);
  }
  if (meta.riskLevel >= 2 && !meta.requiresApproval) {
    throw new Error(
      `[${meta.id}] level-${meta.riskLevel} tools (external communication / high impact) must declare requiresApproval: true`,
    );
  }
  if (spec.verify && !meta.mutating) {
    throw new Error(`[${meta.id}] verify() is only meaningful for a mutating tool`);
  }
  if (meta.implementation === "engine" && typeof spec.execute !== "function") {
    throw new Error(`[${meta.id}] an engine tool must provide execute()`);
  }
  if (meta.implementation === "data_plane") {
    // A data-plane tool must carry no body here. If it did, the executor could
    // run a credentialed action inside a process that holds no credentials and
    // no audit database — the exact thing this split prevents.
    if (spec.execute) {
      throw new Error(
        `[${meta.id}] a data_plane tool must not define execute() in the engine — its body lives in backend/services/os_tools/`,
      );
    }
    if (spec.verify) {
      throw new Error(
        `[${meta.id}] a data_plane tool must not define verify() in the engine — its verifier lives in backend/services/os_tools/`,
      );
    }
  }

  return {
    id: meta.id,
    displayName: meta.displayName,
    description: meta.description,
    department: meta.department,
    requiredConnectors: meta.requiredConnectors,
    implementation: meta.implementation as ToolImplementation,
    riskLevel: meta.riskLevel as RiskLevel,
    mutating: meta.mutating,
    requiresApproval: meta.requiresApproval,
    inputSchema: spec.inputSchema,
    outputSchema: spec.outputSchema,
    execute: spec.execute,
    verify: spec.verify,
  };
}
