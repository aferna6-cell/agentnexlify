/**
 * Department-head factory (Agent Library v2).
 *
 * Routing scores departments by skill keywords AND declared semantics
 * (intent / subject). A department is reachable for what it can do, not
 * only for words its drafting skills happen to mention.
 *
 * Agents never call tools. They return a tool request; `executeAction()`
 * is the only place policy, approval, verification, and audit run.
 */

import {
  defineAgent,
  PLAIN_TEXT_CHANNELS,
  type Agent,
  type AgentBucket,
  type AgentChannel,
} from "./_schema.ts";
import {
  readAskIntent,
  type AskIntent,
  type SubjectType,
  type TaskIntent,
} from "./_intent.ts";
import type {
  AgentOutput,
  AgentRunArgs,
  SharedContext,
} from "../types/agent.ts";
import { executeAction } from "../actions/executor.ts";
import { hasActionStore } from "../actions/store.ts";
import { hasToolPorts } from "../actions/ports.ts";

export interface DepartmentActionRequest {
  toolId: string;
  input: Record<string, unknown>;
  describe?: (result: unknown) => string;
  describePending?: (input: Record<string, unknown>) => string;
}

export interface ClarificationRequest {
  clarify: string;
}

export function isClarification(
  r: DepartmentActionRequest | ClarificationRequest | undefined,
): r is ClarificationRequest {
  return Boolean(r && "clarify" in r);
}

export interface DepartmentSkill {
  agent: Agent;
  extraKeywords?: string[];
  servesIntents?: TaskIntent[];
  generative?: boolean;
}

export interface DepartmentSemantics {
  subjects: SubjectType[];
  intents: TaskIntent[];
  primaryIntents?: TaskIntent[];
}

export interface DepartmentSpec {
  agent_id: string;
  display_name: string;
  bucket: AgentBucket;
  channel: AgentChannel;
  purpose: string;
  routes_here_when: string[];
  strong_signals?: string[];
  semantics?: DepartmentSemantics;
  skills: DepartmentSkill[];
  defaultSkillId: string;
  resolveSkill?: (args: {
    ownerAsk: string;
    params: Record<string, unknown>;
    context: SharedContext;
    intent: AskIntent;
  }) => string | undefined;
  resolveAction?: (args: {
    ownerAsk: string;
    params: Record<string, unknown>;
    context: SharedContext;
    intent: AskIntent;
  }) => DepartmentActionRequest | ClarificationRequest | undefined;
  resolveActionFromOutput?: (args: {
    ownerAsk: string;
    params: Record<string, unknown>;
    context: SharedContext;
    intent: AskIntent;
    output: AgentOutput;
  }) => DepartmentActionRequest | undefined;
  examples: {
    owner_ask: string;
    expected_route: string;
    expected_output_excerpt: string;
  }[];
}

function scoreSkill(ask: string, skill: DepartmentSkill): number {
  const a = ask.toLowerCase();
  let score = 0;
  for (const kw of skill.agent.keywords)
    if (a.includes(kw.toLowerCase())) score += 1;
  for (const sig of skill.agent.strong_signals)
    if (a.includes(sig.toLowerCase())) score += 3;
  for (const kw of skill.extraKeywords ?? [])
    if (a.includes(kw.toLowerCase())) score += 2;
  return score;
}

export function eligibleSkills(
  spec: DepartmentSpec,
  intent: AskIntent | undefined,
): DepartmentSkill[] {
  if (!intent) return spec.skills;
  const eligible = spec.skills.filter((skill) => {
    if (skill.servesIntents && !skill.servesIntents.includes(intent.intent))
      return false;
    if (skill.generative && intent.subjectExists) return false;
    if (skill.generative && intent.intent === "communicate") return false;
    return true;
  });
  return eligible.length > 0 ? eligible : spec.skills;
}

export function pickSkill(
  spec: DepartmentSpec,
  ask: string,
  intent?: AskIntent,
): DepartmentSkill {
  const candidates = eligibleSkills(spec, intent);
  let best: DepartmentSkill | undefined;
  let bestScore = 0;
  for (const skill of candidates) {
    const s = scoreSkill(ask, skill);
    if (s > bestScore) {
      bestScore = s;
      best = skill;
    }
  }
  if (best) return best;
  const fallback = candidates.find(
    (s) => s.agent.agent_id === spec.defaultSkillId,
  );
  return fallback ?? candidates[0]!;
}

export function departmentSemanticScore(
  spec: DepartmentSpec,
  intent: AskIntent,
): number {
  const sem = spec.semantics;
  if (!sem) return 0;
  if (sem.primaryIntents?.includes(intent.intent)) return 20;
  const subjectHit = sem.subjects.includes(intent.subjectType);
  const intentHit = sem.intents.includes(intent.intent);
  if (subjectHit && intentHit) return 8;
  if (subjectHit) return 4;
  if (intentHit) return 2;
  return 0;
}

export type DepartmentAgent = Agent & { __department: DepartmentSpec };

export function defineDepartment(spec: DepartmentSpec): DepartmentAgent {
  const keywords = [
    ...new Set(
      spec.skills.flatMap((s) => [
        ...s.agent.keywords,
        ...(s.extraKeywords ?? []),
      ]),
    ),
  ];
  const strongSignals = [
    ...new Set([
      ...(spec.strong_signals ?? []),
      ...spec.skills.flatMap((s) => s.agent.strong_signals),
    ]),
  ];

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
      shared_context_needed: [
        "business_profile",
        "widget_history",
        "pipeline_state",
        "agent_run_history",
      ],
      tool_dependencies: ["none"],
      permission_scope: {
        default: "drafts_only",
        require_owner_approval: true,
      },
      triggers_supported: ["manual", "scheduled", "event_based"],
      output_format: {
        title_template: "{department} — {skill}",
        body_constraints: {
          no_markdown: PLAIN_TEXT_CHANNELS.has(spec.channel),
        },
      },
      examples: spec.examples,
    },
    async (args: AgentRunArgs): Promise<AgentOutput> => {
      const intent = readAskIntent(args.ownerAsk);

      const action = await maybeRunAction(spec, args, intent);
      if (action) return action;

      let skill: DepartmentSkill | undefined;
      const forcedId = spec.resolveSkill?.({
        ownerAsk: args.ownerAsk,
        params: args.input,
        context: args.context,
        intent,
      });
      if (forcedId)
        skill = spec.skills.find((s) => s.agent.agent_id === forcedId);
      if (!skill) skill = pickSkill(spec, args.ownerAsk, intent);

      await args.emitTrace.work(
        "select_skill",
        `${spec.display_name} → ${skill.agent.display_name} skill`,
      );

      const out = await skill.agent.run(args);
      out.orchestratorNotes = out.orchestratorNotes ?? [];

      const composedRequest = spec.resolveActionFromOutput?.({
        ownerAsk: args.ownerAsk,
        params: args.input,
        context: args.context,
        intent,
        output: out,
      });
      if (composedRequest) {
        const performed = await runAction(composedRequest, args, spec);
        if (performed) return performed;
      }

      return out;
    },
  );
  return Object.assign(agent, { __department: spec });
}

async function maybeRunAction(
  spec: DepartmentSpec,
  args: AgentRunArgs,
  intent: AskIntent,
): Promise<AgentOutput | undefined> {
  if (!spec.resolveAction) return undefined;

  const request = spec.resolveAction({
    ownerAsk: args.ownerAsk,
    params: args.input,
    context: args.context,
    intent,
  });
  if (!request) return undefined;

  if (isClarification(request)) {
    await args.emitTrace.work("needs_clarification", request.clarify);
    return {
      orchestratorNotes: [request.clarify],
      noDraftReason: "I need one more detail before I can do this.",
      needsClarification: true,
    };
  }

  return runAction(request, args, spec);
}

async function runAction(
  request: DepartmentActionRequest,
  args: AgentRunArgs,
  spec: DepartmentSpec,
): Promise<AgentOutput | undefined> {
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
      notes.push(
        request.describe
          ? request.describe(outcome.output)
          : `Done — ${request.toolId} completed.`,
      );
      break;
    case "pending_approval":
      notes.push(
        request.describePending
          ? request.describePending(request.input)
          : "That needs your approval before I run it, so I've queued it for review. Approve it and I'll finish the job.",
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
      notes.push(
        `That didn't go through: ${outcome.error ?? "the action failed"}.`,
      );
      break;
  }

  return {
    orchestratorNotes: notes,
    noDraftReason: `This was an action (${request.toolId}), not a draft — see the outcome above.`,
  };
}
