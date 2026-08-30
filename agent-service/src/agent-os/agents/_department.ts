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
  /**
   * What to tell the owner while the action waits for their approval. Say what
   * will happen and to whom — an approval prompt that hides the recipient is
   * not an approval.
   */
  describePending?: (input: Record<string, unknown>) => string;
}

/**
 * A resolver's third answer, beside "act" and "draft": the request was
 * understood and cannot be safely completed, because the information needed to
 * complete it is missing or ambiguous.
 *
 * This exists so that "email Mike about the thing we discussed" — with two
 * Mikes in the pipeline — produces a question rather than a draft to nobody or,
 * worse, a message to the wrong Mike. Ambiguity is an answer, not a failure.
 */
export interface ClarificationRequest {
  clarify: string;
}

export function isClarification(
  r: DepartmentActionRequest | ClarificationRequest | undefined,
): r is ClarificationRequest {
  return Boolean(r && "clarify" in r);
}

export interface DepartmentSkill {
  /** The underlying v1 agent acting as this skill. */
  agent: Agent;
  /** Optional extra trigger words beyond the skill agent's own keywords. */
  extraKeywords?: string[];
  /**
   * Task intents this skill is built to serve. A skill that declares them is
   * excluded from selection for any other intent, however well its keywords
   * score.
   *
   * This is what keeps a quote GENERATOR out of a request to email someone
   * about a quote that already exists. Without it, the word "quote" alone
   * picked the generator, which then refused for want of line items the owner
   * never had reason to supply — a skill contract mismatch that no amount of
   * keyword tuning can fix, because the two asks share every keyword.
   */
  servesIntents?: TaskIntent[];
  /**
   * The skill makes a NEW business object. Such a skill is never right for a
   * request about an object that already exists.
   */
  generative?: boolean;
}

/**
 * What a department owns semantically, independent of the words its skills
 * happen to use.
 *
 * Routing used to be scored purely from the union of skills' keywords, which
 * meant a department could only be reached for things its DRAFTING skills
 * described. A department that can mutate customer records but whose skills all
 * write documents was unreachable for record mutation — not because the
 * capability was missing, but because nothing in the routing surface mentioned
 * it. Declaring semantics separately makes a department reachable for what it
 * can do, not only for what it can write.
 */
export interface DepartmentSemantics {
  /** Business subjects this department is responsible for. */
  subjects: SubjectType[];
  /** Task intents it serves for those subjects. */
  intents: TaskIntent[];
  /**
   * Intents this department owns EXCLUSIVELY. A primary intent outranks any
   * subject noun elsewhere in the sentence, which is what stops "note on Mike's
   * record that he approved the tire quote" from being scored as a quote task.
   */
  primaryIntents?: TaskIntent[];
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
  /** What this department owns, on the intent/subject axes. */
  semantics?: DepartmentSemantics;
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
    intent: AskIntent;
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
    intent: AskIntent;
    departmentId: string;
  }) => DepartmentActionRequest | ClarificationRequest | undefined;
  /**
   * Optional: decide that what the skill just COMPOSED should be performed
   * rather than handed over as a draft — e.g. Sales writing a follow-up the
   * owner asked to email to a named address.
   *
   * Runs after the skill, so the content the owner approves is the content the
   * agent actually wrote. Returning undefined keeps the draft, which is the
   * behaviour that existed before any of this: an ask that is incomplete or
   * ambiguous produces a draft, never an action.
   */
  resolveActionFromOutput?: (args: {
    ownerAsk: string;
    params: Record<string, unknown>;
    context: SharedContext;
    intent: AskIntent;
    output: AgentOutput;
    departmentId: string;
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

/**
 * Which skills are even allowed to serve this ask.
 *
 * Keyword scoring answers "which skill is closest to these words". It cannot
 * answer "which skill is capable of this task", and those are different
 * questions whenever a subject noun is shared across skills. Eligibility is
 * checked first so scoring only ever chooses among skills that could actually
 * succeed.
 */
export function eligibleSkills(
  spec: DepartmentSpec,
  intent: AskIntent | undefined,
): DepartmentSkill[] {
  if (!intent) return spec.skills;
  const eligible = spec.skills.filter((skill) => {
    // A skill that declares the intents it serves does not serve the others.
    if (skill.servesIntents && !skill.servesIntents.includes(intent.intent))
      return false;
    // A skill that makes new business objects is never right for a request
    // about one that already exists: "follow up on the quote we sent her" must
    // not reach a quote generator, whatever the word "quote" scores.
    if (skill.generative && intent.subjectExists) return false;
    if (skill.generative && intent.intent === "communicate") return false;
    return true;
  });
  // Never strand the department: if the intent rules out everything, fall back
  // to the full set rather than failing to answer at all.
  return eligible.length > 0 ? eligible : spec.skills;
}

/** Pick the best-fit skill for an ask within a department (transparent scoring). */
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

/**
 * How well a department matches an ask on the intent/subject axes.
 *
 * Deliberately additive to keyword scoring rather than a replacement: the
 * keyword surface encodes real product knowledge and works for most asks. What
 * it cannot do is reach a department for a capability none of its skills
 * describe, or rank a task above a noun. This supplies both.
 */
export function departmentSemanticScore(
  spec: DepartmentSpec,
  intent: AskIntent,
): number {
  const sem = spec.semantics;
  if (!sem) return 0;

  // An exclusively-owned intent settles the department by itself, so it is
  // weighted to dominate rather than merely to lead. "Primary" is a claim of
  // exclusivity — no other department mutates customer records — and a score
  // that another department's keyword pile can approach would turn that claim
  // into a coin-flip the orchestrator then asks the owner to settle.
  if (sem.primaryIntents?.includes(intent.intent)) return 20;

  const subjectHit = sem.subjects.includes(intent.subjectType);
  const intentHit = sem.intents.includes(intent.intent);
  if (subjectHit && intentHit) return 8;
  if (subjectHit) return 4;
  if (intentHit) return 2;
  return 0;
}

/** A registered department agent that also exposes its skill spec (for tests/admin). */
export type DepartmentAgent = Agent & { __department: DepartmentSpec };

/** Build the registry agent for a department from its skills. */
export function defineDepartment(spec: DepartmentSpec): DepartmentAgent {
  // Aggregate routing signals from all member skills so the orchestrator's
  // classifier can score the department as a 1-of-8 choice.
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
      // The representative channel may be plain-text (e.g. Operations → sms); the
      // real draft channel is set per-skill, but the schema still requires
      // no_markdown to match the declared channel.
      output_format: {
        title_template: "{department} — {skill}",
        body_constraints: {
          no_markdown: PLAIN_TEXT_CHANNELS.has(spec.channel),
        },
      },
      examples: spec.examples,
    },
    async (args: AgentRunArgs): Promise<AgentOutput> => {
      // Read the ask onto its semantic axes once, and hand the same reading to
      // every decision below. Skill choice, action eligibility and clarification
      // all need it, and re-deriving it per consumer is how they drift apart.
      const intent = readAskIntent(args.ownerAsk);

      // Action path first: some asks are things to DO, not things to draft.
      // This runs BEFORE composition on purpose. Resolving an action from
      // composed output alone meant a skill that declined to compose could
      // silently veto an action the owner had clearly authorized.
      const action = await maybeRunAction(spec, args, intent);
      if (action) return action;

      // Context-aware override first (e.g. Sales pipeline lookup), else
      // intent-gated keyword scoring.
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

      // Make the skill decision visible in the reasoning trace (V-02).
      await args.emitTrace.work(
        "select_skill",
        `${spec.display_name} → ${skill.agent.display_name} skill`,
      );

      const out = await skill.agent.run(args);
      out.orchestratorNotes = out.orchestratorNotes ?? [];

      // The composed draft may itself be the thing to perform (e.g. an email
      // the owner asked to send to a named address). The action carries the
      // composed text, so what gets approved is exactly what was written.
      const composedRequest = spec.resolveActionFromOutput?.({
        ownerAsk: args.ownerAsk,
        params: args.input,
        context: args.context,
        intent,
        output: out,
        departmentId: spec.agent_id,
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

/**
 * Run a department's action path, when it has one and this ask matches it.
 *
 * Returns the agent output describing the outcome, or undefined to let the
 * department draft as usual. Every branch is honest: an action awaiting approval
 * says so, a denial says why, and a failure is reported as a failure — nothing
 * here ever reports work that did not happen.
 */
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
    departmentId: spec.agent_id,
  });
  if (!request) return undefined;

  // The resolver understood the task and found it under-specified. Asking is
  // the correct outcome — better than a draft addressed to nobody, and far
  // better than picking one of two customers with the same first name.
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

/**
 * Put one tool request through the action executor and turn the outcome into
 * the owner's answer.
 *
 * Returns undefined when the action layer is not available in this host, so
 * the department falls back to drafting rather than pretending.
 */
async function runAction(
  request: DepartmentActionRequest,
  args: AgentRunArgs,
  spec: DepartmentSpec,
): Promise<AgentOutput | undefined> {
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
