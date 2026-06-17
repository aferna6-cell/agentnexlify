import { z } from "zod";
import { defineAgent } from "../_schema.ts";
import { Authoring, presentProfileFields, firstName } from "../_authoring.ts";
import { finishBody } from "../_format.ts";
import { generateDraft } from "../../lib/draft.ts";
import type { AgentOutput } from "../../types/agent.ts";
import { examples } from "./examples.ts";

const Input = z.object({
  prospect_name: z.string().optional(),
  prospect_business: z.string().optional(),
  prospect_url: z.string().optional(),
  website: z.string().optional(),
  observed_gap: z.string().optional(),
  note: z.string().optional(),
  contact_name: z.string().optional(),
});

/**
 * Pull a prospect business name from the ask when params don't carry one. Catches
 * "reach out to Bayside Plumbing", "cold email to Acme Dental", "prospect Joe's Garage".
 */
function parseProspect(ask: string): string | undefined {
  // Trigger phrase, then optional filler ("a new prospect,", "to", "from", "the"),
  // then the proper-noun business name (1-5 capitalized tokens).
  const m = ask.match(
    /\b(?:reach out to|cold email(?:\s+to)?|cold outreach to|outreach to|email|prospect|contact|message|new business (?:from|with|at)|business (?:from|with|at)|from|to)\s+(?:a |an |the |new |our )*(?:prospect[, ]+|business[, ]+|company[, ]+|called )?([A-Z][\w&'.-]*(?:\s+[A-Z][\w&'.-]*){0,4})/,
  );
  const name = m?.[1]?.trim();
  return name && name.length > 1 ? name : undefined;
}

/** Pull an observed gap / hook from the ask ("they have no website chat", "slow after-hours response"). */
function parseGap(ask: string): string | undefined {
  const m = ask.match(/\b(?:because|since|they|their)\s+(.{6,120})$/i);
  return m?.[1]?.trim();
}

export const outreach = defineAgent(
  {
    agent_id: "outreach",
    display_name: "Outbound Outreach",
    bucket: "sales",
    status: "new",
    build_priority: "P3",
    purpose:
      "Drafts a short, personalized cold-outreach email to a prospect business, using the prospect's own observed gap as the hook. Draft-only; cold outreach is never auto-sent.",
    channel: "email",
    routes_here_when: [
      "Owner asks to cold email or reach out to a prospect business they do not yet do business with",
      "Owner wants outreach to win brand-new business from a named company",
    ],
    keywords: ["cold email", "cold outreach", "reach out to", "prospect", "outreach", "new business"],
    strong_signals: ["cold email", "cold outreach", "reach out to a prospect"],
    shared_context_needed: ["business_profile"],
    tool_dependencies: ["none"],
    permission_scope: {
      default: "drafts_only",
      require_owner_approval: true,
      // Cold outreach to a non-customer must never auto-send.
      never_auto_send: true,
      recipient_filter: "custom_list",
    },
    triggers_supported: ["manual"],
    output_format: { title_template: "Cold outreach - {prospect}", body_constraints: { no_markdown: false } },
    examples,
  },
  async ({ input, context, emitTrace, ownerAsk, runId }): Promise<AgentOutput> => {
    const a = new Authoring(context.businessProfile);
    const p = Input.safeParse(input);
    const params = p.success ? p.data : {};

    const prospect = params.prospect_business?.trim() || params.prospect_name?.trim() || parseProspect(ownerAsk);
    const prospectUrl = params.prospect_url?.trim() || params.website?.trim();
    const gap = params.observed_gap?.trim() || params.note?.trim() || parseGap(ownerAsk);
    const contactName = firstName(params.contact_name);

    await emitTrace.emit("load_business_profile", {
      description: `Loaded business profile (${presentProfileFields(context.businessProfile).join(", ")})`,
      data: presentProfileFields(context.businessProfile),
    });

    const hasProspect = await emitTrace.emit("identify_prospect", {
      description: prospect ? `Prospect: ${prospect}` : "No prospect business identified",
      data: prospect ? { prospect, prospectUrl, gap } : undefined,
    });

    if (!hasProspect) {
      // Honest: no prospect means no draft. Never invent a company to email.
      a.note(
        "I don't have a prospect business to reach out to yet. Tell me who to email (the business name, and their website or the gap you noticed) and I'll draft the outreach.",
      );
      return { orchestratorNotes: a.notes, noDraftReason: "no prospect business provided" };
    }

    const businessName = a.field("businessName");
    const signoff = a.signoff();
    const phone = a.field("phone");
    const email = a.field("email");
    const website = a.field("website");

    // Compliant hook: only assert the gap the owner actually observed; otherwise
    // open on a neutral, honest reason for reaching out (no fabricated claims).
    const hookLine = gap
      ? `I noticed ${gap} on your side, and that's exactly the kind of thing we help local businesses fix.`
      : `I came across ${prospect} and wanted to introduce ourselves.`;

    const senderLine = businessName
      ? `${businessName}${context.businessProfile.industry ? ` (${context.businessProfile.industry})` : ""}`
      : "our team";
    const contactBlock = [phone ? `Phone: ${phone}` : null, email ?? null, website ?? null].filter(Boolean).join("\n");

    const local = (): string => {
      const greeting = contactName ? `Hi ${contactName},` : `Hi there,`;
      const intro = businessName
        ? `I'm with ${senderLine}.`
        : `I'm reaching out from a local business in your area.`;
      const cta = "Open to a quick 10-minute call this week to see if it's a fit? No pressure either way.";
      const sig = signoff ? `\n\nThanks,\n${signoff}${businessName && signoff !== businessName ? `\n${businessName}` : ""}` : "";
      const tail = contactBlock ? `\n\n${contactBlock}` : "";
      return (
        `Subject: A quick idea for ${prospect}\n\n` +
        `${greeting}\n\n` +
        `${intro} ${hookLine}\n\n` +
        `${cta}` +
        `${sig}${tail}`
      );
    };

    const system =
      `${a.promptBlock()}\n\n` +
      `You draft ONE short cold-outreach email on the EMAIL channel (markdown allowed) from the owner to a PROSPECT ` +
      `business the owner does not yet work with. Open the email by personalizing on the prospect's specific gap as the ` +
      `hook${gap ? ` (the gap: "${gap}")` : ", and if no gap is given, use a neutral, honest reason for reaching out"}. ` +
      `Make only honest claims - describe what the owner's business does, never invent results, metrics, or prior contact. ` +
      `Keep it under ~120 words, warm and human, not spammy or hypey. End with ONE soft call to action (a low-pressure ` +
      `offer to talk). Make clear this is a first introduction. Use the owner's real business name and contact info; ` +
      `never emit bracketed placeholders.` +
      (signoff ? ` Sign off as ${signoff}.` : "");
    const prompt =
      `Prospect business: ${prospect}.\n` +
      `Prospect website: ${prospectUrl ?? "(unknown)"}.\n` +
      `Observed gap / hook: ${gap ?? "(none given - use a neutral honest reason)"}.\n` +
      `Contact first name: ${contactName ?? "(unknown)"}.`;

    await emitTrace.work("compose_outreach", `cold email to ${prospect}${gap ? `, hook="${gap}"` : ", neutral hook"}`);
    const generated = await generateDraft({ system, prompt, runId, local });
    if (!generated) {
      a.note("Service is temporarily unavailable - please try again in a few minutes.");
      return { orchestratorNotes: a.notes, noDraftReason: "service temporarily unavailable" };
    }

    return {
      draft: {
        title: `Cold outreach - ${prospect}`,
        body: finishBody("email", generated.text),
        channel: "email",
        metadata: { prospect, prospect_url: prospectUrl, gap, source: generated.source, cost_usd: generated.costUsd },
        requiresApproval: true,
      },
      orchestratorNotes: a.notes,
    };
  },
);
