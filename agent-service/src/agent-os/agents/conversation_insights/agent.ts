import { z } from "zod";
import { defineAgent } from "../_schema.ts";
import { Authoring, presentProfileFields } from "../_authoring.ts";
import { finishBody } from "../_format.ts";
import { generateDraft } from "../../lib/draft.ts";
import type { AgentOutput, SharedContext } from "../../types/agent.ts";
import { examples } from "./examples.ts";

const Input = z.object({
  period: z.string().optional(),
});

interface Section {
  heading: string;
  content: string;
}

/** Count occurrences and return the top-N entries as "label (n)" strings. */
function topCounts(values: string[], limit: number): string[] {
  const counts = new Map<string, number>();
  for (const raw of values) {
    const v = raw.trim();
    if (!v) continue;
    counts.set(v, (counts.get(v) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([label, n]) => (n > 1 ? `${label} (${n})` : label));
}

interface SentimentCounts {
  positive: number;
  neutral: number;
  negative: number;
}

/** Tally stored per-conversation sentiment, ignoring unclassified rows. */
function countSentiment(convos: { sentiment?: string }[]): SentimentCounts {
  const out: SentimentCounts = { positive: 0, neutral: 0, negative: 0 };
  for (const c of convos) {
    const s = (c.sentiment ?? "").trim().toLowerCase();
    if (s === "positive" || s === "neutral" || s === "negative") {
      out[s] += 1;
    }
  }
  return out;
}

/**
 * Build ONLY non-empty sections from real conversation data. Same honest-load
 * rule as the Weekly Briefing: never emit "none this period" filler.
 */
function buildSections(ctx: SharedContext): Section[] {
  const sections: Section[] = [];
  const convos = ctx.widgetHistory;
  const total = convos.length;

  // 1. Volume + contact-capture rate. The Front Desk's whole job is capturing
  // the lead, so capture rate is the headline operational metric.
  if (total > 0) {
    const captured = convos.filter((c) => (c.contactName ?? "").trim().length > 0).length;
    const rate = Math.round((captured / total) * 100);
    sections.push({
      heading: "Volume & capture",
      content: `${total} conversation(s). ${captured} captured a contact (${rate}% capture rate).`,
    });
  }

  // 2. What customers ask about — topics + intent mix. This is the "AI Analytics"
  // surface: the recurring themes the owner can act on.
  if (total > 0) {
    const lines: string[] = [];
    const topics = topCounts(convos.flatMap((c) => c.topics ?? []), 6);
    if (topics.length) lines.push(`Top topics: ${topics.join(", ")}.`);
    const intents = topCounts(
      convos.map((c) => (c.intent ?? "").trim()).filter((i) => i.length > 0),
      5,
    );
    if (intents.length) lines.push(`Intents: ${intents.join(", ")}.`);
    if (lines.length) sections.push({ heading: "What customers ask about", content: lines.join(" ") });
  }

  // 2b. Customer sentiment: real breakdown from the stored per-conversation
  // classification (conversation_enrichment). Only conversations the classifier
  // labelled count toward the breakdown; unlabelled ones are excluded so the
  // numbers stay honest. Section appears only when at least one is labelled.
  const sentimentCounts = countSentiment(convos);
  const labelled = sentimentCounts.positive + sentimentCounts.neutral + sentimentCounts.negative;
  if (labelled > 0) {
    sections.push({
      heading: "Customer sentiment",
      content:
        `${sentimentCounts.positive} positive / ${sentimentCounts.neutral} neutral / ` +
        `${sentimentCounts.negative} negative across ${labelled} classified conversation(s).`,
    });
  }

  // 3. Needs attention (QA) — complaints + knowledge-base gaps. This is the
  // "AI Quality" surface: where the front desk underperformed.
  const attention: string[] = [];
  const complaints = convos.filter((c) => (c.intent ?? "").toLowerCase().includes("complaint"));
  for (const c of complaints) {
    attention.push(`Complaint from ${c.contactName ?? "a customer"}: ${c.summary}`);
  }
  const kbGaps = ctx.agentRunHistory.filter((r) => r.kbGap);
  if (kbGaps.length) {
    const noun = kbGaps.length === 1 ? "question" : "questions";
    attention.push(
      `${kbGaps.length} customer ${noun} your knowledge base didn't cover — add an FAQ entry so the AI answers directly next time.`,
    );
  }
  if (attention.length) {
    sections.push({ heading: "Needs attention", content: attention.map((a) => `- ${a}`).join("\n") });
  }

  // 4. Recommendations — derived from the numbers above, no invention.
  const recs: string[] = [];
  if (total > 0) {
    const captured = convos.filter((c) => (c.contactName ?? "").trim().length > 0).length;
    if (captured / total < 0.5) {
      recs.push("Capture rate is under 50% — have the front desk ask for a name and contact earlier in the chat.");
    }
  }
  if (kbGaps.length) {
    recs.push("Turn the uncovered questions above into FAQ/knowledge-base entries to lift answer coverage.");
  }
  if (complaints.length) {
    recs.push("Review the flagged complaints and confirm each got a follow-up.");
  }
  if (sentimentCounts.negative > 0 && labelled > 0 && sentimentCounts.negative / labelled >= 0.25) {
    recs.push(
      `${sentimentCounts.negative} of ${labelled} classified chats read as negative. Review those transcripts to find what is frustrating customers.`,
    );
  }
  if (recs.length) {
    sections.push({ heading: "Recommendations", content: recs.map((r) => `- ${r}`).join("\n") });
  }

  return sections;
}

export const conversationInsights = defineAgent(
  {
    agent_id: "conversation_insights",
    display_name: "Conversation Insights",
    bucket: "reporting",
    status: "new",
    build_priority: "P2",
    purpose:
      "Analyzes front-desk conversations for volume, capture rate, recurring topics/intents, complaints, and knowledge-base gaps, then recommends fixes.",
    channel: "report",
    routes_here_when: [
      "Owner asks what customers are asking about or for conversation/chat insights",
      "Owner wants a quality read on how the AI front desk is performing",
    ],
    keywords: [
      "conversation insights",
      "customer insights",
      "chat insights",
      "what are customers asking",
      "common questions",
      "recurring questions",
      "conversation report",
      "front desk report",
      "chat trends",
      "themes",
      "capture rate",
      "qa",
    ],
    strong_signals: [
      "conversation insights",
      "customer insights",
      "what are customers asking",
      "common questions",
      "conversation report",
    ],
    shared_context_needed: ["business_profile", "widget_history", "agent_run_history"],
    tool_dependencies: ["none"],
    permission_scope: { default: "drafts_only", require_owner_approval: true },
    triggers_supported: ["manual", "scheduled"],
    trigger_detail: { scheduled_cron: ["0 8 1 * *"] },
    output_format: {
      title_template: "Conversation Insights — {period}",
      body_constraints: { no_markdown: false },
    },
    examples,
  },
  async ({ input, context, emitTrace, runId }): Promise<AgentOutput> => {
    const a = new Authoring(context.businessProfile);
    const p = Input.safeParse(input);
    const params = p.success ? p.data : {};
    const period = params.period?.trim() || "last 30 days";

    await emitTrace.emit("load_business_profile", {
      description: `Loaded business profile (${presentProfileFields(context.businessProfile).join(", ")})`,
      data: presentProfileFields(context.businessProfile),
    });
    await emitTrace.emit("load_conversations", {
      description: `${context.widgetHistory.length} widget conversation(s)`,
      data: context.widgetHistory,
    });
    await emitTrace.emit("load_agent_activity", {
      description: `${context.agentRunHistory.length} agent run(s)`,
      data: context.agentRunHistory,
    });

    const sections = buildSections(context);
    const businessName = a.field("businessName");
    const header = `# Conversation Insights — ${period}${businessName ? ` · ${businessName}` : ""}`;

    const local = (): string => {
      if (sections.length === 0) {
        return `${header}\n\nNo front-desk conversations logged in this period yet. Once the widget starts capturing chats, this report will show what customers ask about, your contact-capture rate, and where the AI needs better answers.`;
      }
      return `${header}\n\n` + sections.map((s) => `## ${s.heading}\n\n${s.content}`).join("\n\n");
    };

    const system =
      `${a.promptBlock()}\n\n` +
      `You write a Conversation Insights report on the REPORT channel (markdown). It tells a small-business owner ` +
      `how their AI front desk is performing: how many chats came in, how many captured a contact, what customers ` +
      `ask about, and where the AI fell short. CRITICAL: include a section ONLY if it has data — never write an ` +
      `empty section or "none this period". Use ONLY the figures provided below; do not invent numbers or topics. ` +
      `If there's no activity, write one short "no conversations yet" line.`;
    const prompt =
      `Period: ${period}.\n` +
      `Available sections (already filtered to non-empty):\n` +
      (sections.length
        ? sections.map((s) => `## ${s.heading}\n${s.content}`).join("\n\n")
        : "(no conversations this period)");

    await emitTrace.work(
      "assemble_insights",
      sections.length ? `included sections: ${sections.map((s) => s.heading).join(", ")}` : "no activity — short no-data note",
    );
    const generated = await generateDraft({ system, prompt, runId, local });
    if (!generated) {
      a.note("Service is temporarily unavailable — please try again in a few minutes.");
      return { orchestratorNotes: a.notes, noDraftReason: "service temporarily unavailable" };
    }

    return {
      draft: {
        title: `Conversation Insights — ${period}`,
        body: finishBody("report", generated.text),
        channel: "report",
        metadata: {
          period,
          sections_included: sections.map((s) => s.heading),
          source: generated.source,
          cost_usd: generated.costUsd,
        },
        requiresApproval: true,
      },
      orchestratorNotes: a.notes,
    };
  },
);
