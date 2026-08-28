/**
 * Department-head factory (Agent Library v2).
 *
 * A department is ONE registry agent that owns a business function and dispatches
 * each ask to the best-fit internal *skill*. Skills are the former v1 worker
 * agents (src/agents/<id>/agent.ts) — their composing logic, trace honesty,
 * Authoring (no-placeholder) and channel formatting are reused verbatim; they are
 * simply no longer registered individually. The owner routes 1-of-8 departments;
 * the department then picks 1-of-N skills.
 *
 * Routing:
 *  - The orchestrator's classifier scores departments by the UNION of their
 *    skills' keywords/strong_signals (aggregated onto the department spec).
 *  - Inside run(), pickSkill() re-scores the same signals scoped to this
 *    department's skills and delegates to the winner's run().
 *
 * Channels: a department spans channels, so its declared `channel` is just a
 * representative (rich) channel for schema purposes; the *draft's* channel is set
 * by whichever skill produced it (each skill already calls finishBody on its own
 * channel, so the plain-text/no_markdown rule still holds on the real output).
 */

import { defineAgent, PLAIN_TEXT_CHANNELS, type Agent, type AgentBucket, type AgentChannel } from "./_schema.ts";
import type { AgentOutput, AgentRunArgs, SharedContext } from "../types/agent.ts";
import { executeAction } from "../actions/executor.ts";
import { hasActionStore } from "../actions/store.ts";
import { hasToolPorts } from "../actions/ports.ts";

/**
 * A department's decision to *do* something instead of drafting something.
 *
 * The department names a tool and its input; the action executor
 * (`actions/executor.ts`) does everything else — policy, approval, execution,
 * verification, audit. A department never calls a tool directly, which is why
 * this type carries no function to run.
 */
export interface DepartmentActionRequest {
  toolId: string;
  input: Record<string, unknown>;
  /** Turns a successful result into the line the owner reads. */
  describe?: (result: unknown) => string;
}

export interface DepartmentSkill {
  /** The underlying v1 agent acting as this skill. */
  agent: Agent;
  /** Optional extra trigger words beyond the skill agent's own keywords. */
  extraKeywords?: string[];
}

export interface DepartmentSpec {
  agent_id: string;
  display_name: string;
  bucket: AgentBucket;
  /** Representative channel for the schema (departments span channels at runtime). */
  channel: AgentChannel;
  purpose: string;
  routes_here_when: string[];
  strong_signals?: string[];
  /** Member skills, in priority order (ties break toward earlier skills). */
  skills: DepartmentSkill[];
  /** Skill chosen when nothing scores (e.g. a department's safe default). */
  defaultSkillId: string;
  /**
   * Optional context-aware override (e.g. Sales inspects pipeline state to pick
   * quote-followup vs quote-generation). Return a skill agent_id to force it, or
   * undefined to fall back to keyword scoring. `params` are the orchestrator's
   * extracted params; `context` is the SharedContext.
   */
  resolveSkill?: (args: {
    ownerAsk: string;
    params: Record<string, unknown>;
    context: SharedContext;
  }) => string | undefined;
  /**
   * Optional: decide that this ask is an ACTION rather than a draft. Return a
   * tool request to run it through the action executor, or undefined to fall
   * through to the normal skill dispatch. Returning undefined must always be
   * safe — a half-understood ask drafts, it never writes.
   */
  resolveAction?: (args: {
    ownerAsk: string;
    params: Record<string, unknown>;
    context: SharedContext;
  }) => DepartmentActionRequest | undefined;
  examples: { owner_ask: string; expected_route: string; expected_output_excerpt: string }[];
}

function scoreSkill(ask: string, skill: DepartmentSkill): number {
  const a = ask.toLowerCase();
  let score = 0;
  for (const kw of skill.agent.keywords) if (a.includes(kw.toLowerCase())) score += 1;
  for (const sig of skill.agent.strong_signals) if (a.includes(sig.toLowerCase())) score += 3;
  for (const kw of skill.extraKeywords ?? []) if (a.includes(kw.toLowerCase())) score += 2;
  return score;
}

/** Pick the best-fit skill for an ask within a department (transparent scoring). */
export function pickSkill(spec: DepartmentSpec, ask: string): DepartmentSkill {
  let best: DepartmentSkill | undefined;
  let bestScore = 0;
  for (const skill of spec.skills) {
    const s = scoreSkill(ask, skill);
    if (s > bestScore) {
      bestScore = s;
      best = skill;
    }
  }
  if (best) return best;
  const fallback = spec.skills.find((s) => s.agent.agent_id === spec.defaultSkillId);
  return fallback ?? spec.skills[0]!;
}

/** A registered department agent that also exposes its skill spec (for tests/admin). */
export type DepartmentAgent = Agent & { __department: DepartmentSpec };

/** Build the registry agent for a department from its skills. */
export function defineDepartment(spec: DepartmentSpec): DepartmentAgent {
  // Aggregate routing signals from all member skills so the orchestrator's
  // classifier can score the department as a 1-of-8 choice.
  const keywords = [...new Set(spec.skills.flatMap((s) => [...s.agent.keywords, ...(s.extraKeywords ?? [])]))];
  const strongSignals = [...new Set([...(spec.strong_signals ?? []), ...spec.skills.flatMap((s) => s.agent.strong_signals)])];

  const agent = defineAgent(
    {
      agent_id: spec.agent_id,
      display_name: spec.display_name,
      bucket: spec.bucket,
      status: "existing",
      build_priority: "P1",
      purpose: spec.purpose,
      channel: spec.channel,
      routes_here_when: spec.routes_here_when,
      keywords,
      strong_signals: strongSignals,
      shared_context_needed: ["business_profile", "widget_history", "pipeline_state", "agent_run_history"],
      tool_dependencies: ["none"],
      permission_scope: { default: "drafts_only", require_owner_approval: true },
      triggers_supported: ["manual", "scheduled", "event_based"],
      // The representative channel may be plain-text (e.g. Operations → sms); the
      // real draft channel is set per-skill, but the schema still requires
      // no_markdown to match the declared channel.
      output_format: { title_template: "{department} — {skill}", body_constraints: { no_markdown: PLAIN_TEXT_CHANNELS.has(spec.channel) } },
      examples: spec.examples,
    },
    async (args: AgentRunArgs): Promise<AgentOutput> => {
      // Action path first: some asks are things to DO, not things to draft.
      const action = await maybeRunAction(spec, args);
      if (action) return action;

      // Context-aware override first (e.g. Sales pipeline lookup), else keyword scoring.
      let skill: DepartmentSkill | undefined;
      const forcedId = spec.resolveSkill?.({ ownerAsk: args.ownerAsk, params: args.input, context: args.context });
      if (forcedId) skill = spec.skills.find((s) => s.agent.agent_id === forcedId);
      if (!skill) skill = pickSkill(spec, args.ownerAsk);

      // Make the skill decision visible in the reasoning trace (V-02).
      await args.emitTrace.work("select_skill", `${spec.display_name} → ${skill.agent.display_name} skill`);

      const out = await skill.agent.run(args);
      out.orchestratorNotes = out.orchestratorNotes ?? [];
      return out;
    },
  );
  return Object.assign(agent, { __department: spec });
}

/**
 * Run a department's action path, when it has one and this ask matches it.
 *
 * Returns the agent output describing the outcome, or undefined to let the
 * department draft as usual. Every branch is honest: an action awaiting approval
 * says so, a denial says why, and a failure is reported as a failure — nothing
 * here ever reports work that did not happen.
 */
async function maybeRunAction(spec: DepartmentSpec, args: AgentRunArgs): Promise<AgentOutput | undefined> {
  if (!spec.resolveAction) return undefined;

  const request = spec.resolveAction({ ownerAsk: args.ownerAsk, params: args.input, context: args.context });
  if (!request) return undefined;

  // The action layer needs a tenant to act for and a host that wired its seams.
  // Where either is missing (e.g. a unit test running an agent in isolation) the
  // department falls back to drafting and says so in the trace rather than
  // pretending an action happened.
  if (!args.userId || !hasActionStore() || !hasToolPorts()) {
    await args.emitTrace.fallback(
      "tool_unavailable",
      "The action layer isn't available here, so I'll prepare this as a draft instead.",
    );
    return undefined;
  }

  const outcome = await executeAction({
    accountId: args.userId,
    runId: args.runId,
    agentId: spec.agent_id,
    toolId: request.toolId,
    input: request.input,
    sharedContext: args.context,
    trace: args.emitTrace,
  });

  const notes: string[] = [];
  switch (outcome.status) {
    case "succeeded":
      notes.push(request.describe ? request.describe(outcome.output) : `Done — ${request.toolId} completed.`);
      break;
    case "pending_approval":
      notes.push(
        "That needs your approval before I run it, so I've queued it for review. Approve it and I'll finish the job.",
      );
      break;
    case "denied":
      notes.push(`I couldn't do that: ${outcome.record.policyReason}.`);
      break;
    case "verification_failed":
      notes.push(
        `I ran that, but couldn't confirm it saved: ${outcome.record.verificationDetail ?? "the record could not be read back"}. Please check before relying on it.`,
      );
      break;
    default:
      notes.push(`That didn't go through: ${outcome.error ?? "the action failed"}.`);
      break;
  }

  return {
    orchestratorNotes: notes,
    noDraftReason: `This was an action (${request.toolId}), not a draft — see the outcome above.`,
  };
}
