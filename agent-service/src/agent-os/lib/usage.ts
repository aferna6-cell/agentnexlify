/**
 * Usage caps — no-op in the agent-service runtime.
 *
 * The standalone enforced a daily demo-spend cap by counting ModelCallLog rows
 * in Prisma. In production, usage metering and caps live in the FastAPI data
 * plane (os_tenant_usage / ai_usage_guard), so the engine never gates itself
 * here. `anthropic.ts` imports `isCapExceeded()`; it always reports "not
 * exceeded" and the data plane refuses over-budget tenants before it ever calls
 * the orchestrator.
 */

export const ROUTING_CAP = Number(process.env.USAGE_CAP_ROUTING ?? 0);
export const DRAFT_CAP = Number(process.env.USAGE_CAP_DRAFT ?? 0);

export async function isCapExceeded(_purpose: "routing" | "draft" | "other"): Promise<boolean> {
  return false;
}
