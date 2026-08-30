/**
 * Action policy — one place decides whether a tool may run.
 *
 * Agents do not check permissions. Routers do not check permissions. Tools do
 * not check permissions. `evaluateActionPolicy` does, and the executor is the
 * only caller. That is what makes the rule auditable: every execution row stores
 * the decision and the reason that produced it.
 *
 * Default policy, by risk level:
 *   0 read-only              -> allow
 *   1 internal mutation      -> allow (reversible, stays inside the tenant)
 *   2 external communication -> require approval
 *   3 financial / legal      -> require approval, always
 *
 * A tenant may tighten this (lower `approvalThreshold`, disable tools, pin
 * specific tools to always-approve). A tenant may never loosen a level-3
 * requirement, and may never drop an approval a tool itself declared.
 */

import type { RiskLevel } from "./types.ts";
import {
  SEND_EMAIL_TOOL_ID,
  canProposeSendEmail,
  sendEmailEnabled,
} from "./flags.ts";

/**
 * The only tool facts policy needs. Keeping this narrow means policy never
 * depends on a tool's schemas or behaviour — and it can be exercised in tests
 * with a plain object.
 */
export interface PolicyTool {
  id: string;
  riskLevel: RiskLevel;
  requiresApproval: boolean;
}

export type PolicyDecision = "allow" | "requires_approval" | "deny";

export interface TenantToolPolicy {
  /** Allow-list. When set, a tool outside it is denied (per-tenant integrations). */
  enabledToolIds?: string[];
  /** Deny-list, applied after the allow-list. */
  disabledToolIds?: string[];
  /**
   * Risk level at or above which approval is required. Defaults to 2.
   * Values above 3 are clamped: level 3 always requires approval.
   */
  approvalThreshold?: RiskLevel;
  /** Tools that always require approval for this tenant, whatever their level. */
  alwaysApproveToolIds?: string[];
}

export interface PolicyContext {
  accountId: string;
  agentId?: string;
  policy?: TenantToolPolicy;
}

export interface PolicyEvaluation {
  decision: PolicyDecision;
  riskLevel: RiskLevel;
  /** True when the action may only run after an explicit approval. */
  requiresApproval: boolean;
  /** Short, human-readable justification, persisted on the execution row. */
  reason: string;
}

export const DEFAULT_APPROVAL_THRESHOLD: RiskLevel = 2;

/** The policy used when a host registers none. */
export const DEFAULT_TOOL_POLICY: TenantToolPolicy = {};

export interface ToolPolicyProvider {
  /** Resolve the policy for one tenant. Never throws — return defaults instead. */
  load(accountId: string): Promise<TenantToolPolicy>;
}

let provider: ToolPolicyProvider | null = null;

/** Hosts register a provider to make policy tenant-specific. Optional. */
export function setToolPolicyProvider(p: ToolPolicyProvider): void {
  provider = p;
}

export function hasToolPolicyProvider(): boolean {
  return provider !== null;
}

/** Test/diagnostic hook. */
export function resetToolPolicyProvider(): void {
  provider = null;
}

/**
 * Resolve a tenant's policy. Absence of a provider is not an error — it means
 * "use the safe defaults" — but a provider that throws must not silently widen
 * permissions, so a failure also falls back to the defaults.
 */
export async function loadToolPolicy(
  accountId: string,
): Promise<TenantToolPolicy> {
  if (!provider) return DEFAULT_TOOL_POLICY;
  try {
    return (await provider.load(accountId)) ?? DEFAULT_TOOL_POLICY;
  } catch {
    return DEFAULT_TOOL_POLICY;
  }
}

/**
 * Decide whether this tool, for this tenant, may execute now.
 *
 * `input` is accepted (and reserved) so input-sensitive rules — a refund over
 * $500, a recipient outside the customer list — can land here later without
 * touching a single call site. It is intentionally unused today rather than
 * inventing rules no product decision has been made about.
 */
export function evaluateActionPolicy(
  tool: PolicyTool,
  _input: unknown,
  context: PolicyContext,
): PolicyEvaluation {
  const policy = context.policy ?? DEFAULT_TOOL_POLICY;
  const riskLevel = tool.riskLevel;

  if (tool.id === SEND_EMAIL_TOOL_ID && !canProposeSendEmail(context.agentId)) {
    return {
      decision: "deny",
      riskLevel,
      requiresApproval: false,
      reason: !sendEmailEnabled()
        ? "send_email is disabled (SEND_EMAIL_ENABLED defaults off)"
        : "send_email is only available to the Sales department",
    };
  }

  if (policy.enabledToolIds && !policy.enabledToolIds.includes(tool.id)) {
    return {
      decision: "deny",
      riskLevel,
      requiresApproval: false,
      reason: `tool "${tool.id}" is not enabled for this business`,
    };
  }
  if (policy.disabledToolIds?.includes(tool.id)) {
    return {
      decision: "deny",
      riskLevel,
      requiresApproval: false,
      reason: `tool "${tool.id}" is disabled for this business`,
    };
  }

  if (riskLevel >= 3) {
    return {
      decision: "requires_approval",
      riskLevel,
      requiresApproval: true,
      reason:
        "level 3 (financial, legal, or destructive) always requires explicit approval",
    };
  }
  if (tool.requiresApproval) {
    return {
      decision: "requires_approval",
      riskLevel,
      requiresApproval: true,
      reason: `tool "${tool.id}" declares that it requires approval`,
    };
  }
  if (policy.alwaysApproveToolIds?.includes(tool.id)) {
    return {
      decision: "requires_approval",
      riskLevel,
      requiresApproval: true,
      reason: `this business requires approval for "${tool.id}"`,
    };
  }

  const threshold = policy.approvalThreshold ?? DEFAULT_APPROVAL_THRESHOLD;
  if (riskLevel >= threshold) {
    return {
      decision: "requires_approval",
      riskLevel,
      requiresApproval: true,
      reason: `risk level ${riskLevel} is at or above this business's approval threshold (${threshold})`,
    };
  }

  return {
    decision: "allow",
    riskLevel,
    requiresApproval: false,
    reason:
      riskLevel === 0
        ? "read-only action, no approval required"
        : `risk level ${riskLevel} is below this business's approval threshold (${threshold})`,
  };
}
