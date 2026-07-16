import { z } from "zod";
import { defineAgent } from "../_schema.ts";
import { Authoring, presentProfileFields } from "../_authoring.ts";
import { finishBody } from "../_format.ts";
import { completeWithWebSearch, isModelAvailable } from "../../lib/anthropic.ts";
import type { AgentOutput } from "../../types/agent.ts";
import { examples } from "./examples.ts";

const Input = z.object({
  topic: z.string().optional(),
  focus: z.string().optional(),
});

function topicOf(ask: string): string {
  return ask
    .replace(/^(research|look into|look up|find out about|find out|investigate|dig into)\s*/i, "")
    .replace(/\bfor (our|my|the) business\b/i, "")
    .trim();
}

/**
 * Market Research skill (Marketing department).
 *
 * The one Agent OS worker that reaches OUTSIDE the tenant's own data: it runs
 * Anthropic's server-side web_search to ground answers on live web results
 * (competitor pricing, local trends, what customers are saying). Produces a
 * REPORT-channel deliverable - display-only, no send action - structured as
 * findings, what it means for this business, and sources.
 *
 * No local fallback on purpose: an offline composer cannot search the web,
 * and an ungrounded "research" draft is worse than an honest outage message.
 */
export const marketResearch = defineAgent(
  {
    agent_id: "market_research",
    display_name: "Market Research",
    bucket: "marketing",
    status: "new",
    build_priority: "P2",
    purpose: "Web-grounded research: competitor pricing, local market trends, customer sentiment, and topic deep-dives with cited sources.",
    channel: "report",
    routes_here_when: [
      "Owner asks to research a topic, competitor, or market",
      "Owner asks what things cost elsewhere or what people are saying about something",
    ],
    keywords: [
      "research", "look into", "look up", "find out", "what are people saying",
      "competitors", "competitor", "market research", "trends", "going rate",
      "what do others charge", "compare prices", "industry",
    ],
    strong_signals: ["research", "what are people saying", "going rate"],
    shared_context_needed: ["business_profile"],
    tool_dependencies: ["none"],
    permission_scope: { default: "drafts_only", require_owner_approval: true },
    triggers_supported: ["manual"],
    output_format: { title_template: "Research — {topic}", body_constraints: { no_markdown: false } },
    examples,
  },
  async ({ input, context, emitTrace, ownerAsk, runId }): Promise<AgentOutput> => {
    const a = new Authoring(context.businessProfile);
    const p = Input.safeParse(input);
    const params = p.success ? p.data : {};
    const topic = params.topic?.trim() || topicOf(ownerAsk) || ownerAsk;

    await emitTrace.emit("load_business_profile", {
      description: `Loaded business profile (${presentProfileFields(context.businessProfile).join(", ")})`,
      data: presentProfileFields(context.businessProfile),
    });

    if (!isModelAvailable()) {
      a.note(
        "Web research needs the live research service, which is temporarily unavailable — please try again in a few minutes.",
      );
      return { orchestratorNotes: a.notes, noDraftReason: "web research requires the live model" };
    }

    const businessType = a.field("businessType");
    const city = a.field("city");
    const state = a.field("state");
    const place = [city, state].filter(Boolean).join(", ");

    const system =
      `${a.promptBlock()}\n\n` +
      `You are a practical research assistant for this small business. Use web search to ` +
      `ground every claim on current sources - never invent facts, prices, or statistics. ` +
      `Write on the REPORT channel (full markdown). Structure the report exactly as:\n` +
      `## What I found\n(3-6 concise findings, each grounded in a source)\n` +
      `## What it means for your business\n(2-4 specific, actionable takeaways` +
      `${businessType ? ` for a ${businessType}` : ""}${place ? ` in ${place}` : ""})\n` +
      `## Sources\n(the URLs you actually used, one per line)`;

    const prompt =
      `Research request from the owner: ${topic}` +
      (params.focus ? `\nFocus: ${params.focus}` : "") +
      (place ? `\nBusiness location: ${place}` : "");

    await emitTrace.work("web_research", `topic="${topic}"`);
    try {
      const r = await completeWithWebSearch({ system, prompt, runId, maxTokens: 2048 });
      if (!r.text.trim()) {
        a.note("The research service returned nothing usable — please try again.");
        return { orchestratorNotes: a.notes, noDraftReason: "empty research result" };
      }
      return {
        draft: {
          title: `Research — ${topic.slice(0, 120)}`,
          body: finishBody("report", r.text),
          channel: "report",
          metadata: { topic, source: "model", cost_usd: r.costUsd },
          requiresApproval: true,
        },
        orchestratorNotes: a.notes,
      };
    } catch {
      a.note(
        "Web research is temporarily unavailable — please try again in a few minutes.",
      );
      return { orchestratorNotes: a.notes, noDraftReason: "web research service unavailable" };
    }
  },
);
