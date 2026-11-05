import { z } from "zod";
import { isBusinessKnowledgeQuestion } from "../_intent.ts";
import { defineAgent } from "../_schema.ts";
import {
  Authoring,
  presentProfileFields,
  firstName,
  greetingInstruction,
} from "../_authoring.ts";
import { finishBody } from "../_format.ts";
import { generateDraft } from "../../lib/draft.ts";
import type { AgentOutput, KbEntry, SharedContext } from "../../types/agent.ts";
import { examples } from "./examples.ts";

const Input = z.object({
  customer_question: z.string().optional(),
  customer_name: z.string().optional(),
  customer_context: z.string().optional(),
});

const INTERNAL_KB =
  /your knowledge about this business is incomplete|still missing:|what we are not building|weave one of these questions|setup gaps|never interrogate|system instruction|knowledge-gap/i;

function isInternalKnowledge(entry: KbEntry): boolean {
  if (entry.internal) return true;
  return INTERNAL_KB.test(`${entry.topic} ${entry.answer}`);
}

function searchKb(kb: KbEntry[], query: string): KbEntry[] {
  const terms = query
    .toLowerCase()
    .split(/\W+/)
    .filter((t) => t.length > 3);
  if (terms.length === 0) return [];
  return kb.filter((e) => {
    if (isInternalKnowledge(e)) return false;
    const hay = `${e.topic} ${e.answer}`.toLowerCase();
    return terms.some((t) => hay.includes(t));
  });
}

function isEchoFragment(text: string, terms: string[]): boolean {
  const words = text
    .toLowerCase()
    .split(/\W+/)
    .filter((w) => w.length > 2);
  if (words.length === 0) return true;
  const informative = words.filter((w) => !terms.some((t) => w.includes(t)));
  return text.length < 80 && informative.length < 2;
}

const ENGINEERING =
  /\{[A-Za-z_][A-Za-z0-9_]*\}|new behavior\s*:|\b\d+\.\s+if the\b/i;

const PROMPT_INJECTION =
  /ignore (?:all |any |previous |prior |above |the ){0,4}instructions|\byou are now\b|\bsystem override\b|\bdisable approval\b|\bsend without approval\b|\bsystem prompt\b|\breveal (?:the |your )?(?:hidden |system )?(?:prompt|instructions|rules)\b/i;

/** Function words only. Content words, negations, and quantifiers stay checkable. */
const GLUE = new Set(
  "a an the and or we our you your i is are was were be it its this that these those of to for in on at with during from as by".split(
    " ",
  ),
);

const MAX_ANSWER_CHARS = 2000;
const MAX_SNIPPET_CHARS = 8000;
const MAX_CLAIMS = 400;

const ANSWER_SYSTEM =
  "Answer only from these snippets. Be concise and customer-facing. " +
  "No internal notes, no implementation plans, no template placeholders, and do not repeat the question. " +
  "If the snippets do not contain the answer, say you do not have that yet.";

/** FAQ rows store the question on the topic. The model only sees the answer. */
export function faqAnswerText(entry: KbEntry): string {
  const topic = (entry.topic || "").replace(/\s+/g, " ").trim();
  let answer = (entry.answer || "").replace(/\s+/g, " ").trim();
  if (
    topic.endsWith("?") &&
    answer.toLowerCase().startsWith(topic.toLowerCase())
  ) {
    answer = answer
      .slice(topic.length)
      .replace(/^[\s:—-]+/, "")
      .trim();
  }
  const embedded = answer.match(/^([^?]{12,}\?)\s+(\S[\s\S]+)$/);
  if (embedded?.[2] && !embedded[2].includes("?")) answer = embedded[2].trim();
  return answer;
}

export function isEngineeringSnippet(text: string): boolean {
  return ENGINEERING.test(text);
}

/** Spec notes, internal copy, prompt injection, and template placeholders. */
export function isExcludedCustomerText(text: string): boolean {
  return (
    isEngineeringSnippet(text) ||
    INTERNAL_KB.test(text) ||
    PROMPT_INJECTION.test(text)
  );
}

/** A complete customer sentence. Truncated spans and bare questions are not. */
export function isWholeCustomerAnswer(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 24) return false;
  if (/\.\.\./.test(trimmed)) return false;
  if (!/[.!]["']?$/.test(trimmed)) return false;
  if (/^[a-z(]/.test(trimmed)) return false;
  if (/\?\s*$/.test(trimmed)) return false;
  if (isExcludedCustomerText(trimmed)) return false;
  return true;
}

/** Top snippets for the model: FAQ answers, not questions, and no spec notes. */
export function customerFacingSnippets(
  question: string,
  hits: KbEntry[],
): string[] {
  const terms = question
    .toLowerCase()
    .split(/\W+/)
    .filter((term) => term.length > 3);
  const ranked = hits
    .filter((entry) => !isInternalKnowledge(entry))
    .map((entry) => faqAnswerText(entry))
    .filter(
      (text) =>
        text &&
        !isExcludedCustomerText(text) &&
        !isEchoFragment(text, terms) &&
        !/^\s*[^?]{0,160}\?\s*$/.test(text),
    )
    .map((text) => {
      const hay = text.toLowerCase();
      const score = terms.reduce(
        (n, term) => n + (hay.includes(term) ? 1 : 0),
        0,
      );
      return { text, score };
    })
    .sort((a, b) => b.score - a.score || b.text.length - a.text.length);

  const picked: string[] = [];
  const seen = new Set<string>();
  for (const row of ranked) {
    const key = row.text.toLowerCase().slice(0, 96);
    if (seen.has(key)) continue;
    seen.add(key);
    picked.push(row.text);
    if (picked.length >= 5) break;
  }
  return picked;
}

export function businessAnswerPrompt(
  question: string,
  snippets: string[],
): string {
  const body = snippets.length
    ? snippets.map((snippet) => `- ${snippet}`).join("\n")
    : "(no snippets)";
  return `Question: ${question}\n\nSnippets:\n${body}`;
}

function normalizeSpace(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

type ClaimIndex = { words: string[]; markers: string[] };

/** Prices, ratios, clock times, and other numbers are atomic. Words are split after. */
function claimIndex(text: string): ClaimIndex {
  let rest = text.toLowerCase();
  const markers: string[] = [];
  const take = (pattern: RegExp, normalize: (match: string) => string) => {
    rest = rest.replace(pattern, (match) => {
      markers.push(normalize(match));
      return " ";
    });
  };
  take(/\$\d{1,3}(?:,\d{3})*(?:\.\d+)?|\$\d+(?:\.\d+)?/g, (match) =>
    match.replace(/[$,]/g, ""),
  );
  take(/\b\d+\s*\/\s*\d+\b/g, (match) => match.replace(/\s+/g, ""));
  take(/\b\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?\b/gi, (match) =>
    match.replace(/[\s.]/g, ""),
  );
  take(/\b\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?)\b/gi, (match) =>
    match.replace(/[\s.]/g, ""),
  );
  take(/\b\d+\.\d+\b/g, (match) => match);
  take(/\b\d+\b/g, (match) => match);
  const words = rest
    .split(/[^a-z']+/)
    .map((word) => word.replace(/^'+|'+$/g, ""))
    .filter((word) => word.length > 0 && !GLUE.has(word));
  return { words, markers };
}

/**
 * Every content word and every number in the answer must occur in the snippets.
 * A new word is an unsupported claim. This is closed-world overlap, not a
 * denylist of particular phrases.
 */
export function isGroundedInSnippets(
  text: string,
  snippets: string[],
): boolean {
  const answer = normalizeSpace(text);
  if (!answer || answer.length > MAX_ANSWER_CHARS) return false;
  if (isExcludedCustomerText(answer)) return false;
  const support = claimIndex(
    normalizeSpace(snippets.join("\n")).slice(0, MAX_SNIPPET_CHARS),
  );
  const words = new Set(support.words);
  const markers = new Set(support.markers);
  const claims = claimIndex(answer);
  const total = claims.words.length + claims.markers.length;
  if (total === 0 || total > MAX_CLAIMS) return false;
  for (const word of claims.words) {
    if (!words.has(word)) return false;
  }
  for (const marker of claims.markers) {
    if (!markers.has(marker)) return false;
  }
  return true;
}

/** Used only when the model is down. Whole FAQ answers, never spliced spans. */
export function extractiveKbAnswer(
  _question: string,
  snippets: string[],
): string {
  const whole = snippets.filter(isWholeCustomerAnswer);
  if (whole.length === 0)
    return "I don't have that in your knowledge base yet.";
  return whole.slice(0, 3).join(" ");
}

export function synthesizeKbAnswer(question: string, hits: KbEntry[]): string {
  return extractiveKbAnswer(question, customerFacingSnippets(question, hits));
}

async function answerFromKnowledge(
  question: string,
  hits: KbEntry[],
  runId: string,
): Promise<string> {
  const snippets = customerFacingSnippets(question, hits);
  const generated = await generateDraft({
    system: ANSWER_SYSTEM,
    prompt: businessAnswerPrompt(question, snippets),
    runId,
    maxTokens: 400,
  });
  const text = generated?.text?.replace(/\s+/g, " ").trim() ?? "";
  // One provider attempt. Unsupported claims are discarded here; there is
  // no verifier call and no second draft.
  if (text && isGroundedInSnippets(text, snippets)) return text;
  return extractiveKbAnswer(question, snippets);
}

function deriveTopic(q: string): string {
  const a = q.toLowerCase();
  if (a.includes("hour")) return "hours";
  if (a.includes("price") || a.includes("cost") || a.includes("how much"))
    return "pricing";
  if (a.includes("hybrid") || a.includes("battery")) return "hybrid service";
  if (a.includes("walk")) return "walk-ins";
  const words = q.trim().split(/\s+/).slice(0, 4).join(" ");
  return words.length ? words : "question";
}

export const customerQuestion = defineAgent(
  {
    agent_id: "customer_question",
    display_name: "Customer Question",
    bucket: "customer_service",
    status: "existing",
    build_priority: "P1",
    purpose:
      "Drafts written answers to customer questions about hours, services, pricing, policies, or products.",
    channel: "widget_reply",
    routes_here_when: [
      "Owner pastes a customer question and asks for a reply",
      "(Phase 4) new widget conversation classified as 'question' intent",
    ],
    keywords: [
      "question",
      "asked",
      "reply",
      "respond",
      "answer",
      "hours",
      "do you",
      "what time",
      "customer asked",
    ],
    strong_signals: ["draft a response", "draft a reply", "how do i reply"],
    shared_context_needed: ["business_profile", "widget_history", "kb"],
    tool_dependencies: ["none"],
    permission_scope: { default: "drafts_only", require_owner_approval: true },
    triggers_supported: ["manual", "event_based"],
    trigger_detail: { events: ["widget_conversation_question"] },
    output_format: {
      title_template: "Reply to {customer} — {topic}",
      body_constraints: { no_markdown: true },
    },
    examples,
  },
  async ({
    input,
    context,
    emitTrace,
    ownerAsk,
    runId,
  }): Promise<AgentOutput> => {
    const a = new Authoring(context.businessProfile);
    const p = Input.safeParse(input);
    const params = p.success ? p.data : {};
    const question = (params.customer_question ?? "").trim() || ownerAsk;
    const customerName = params.customer_name?.trim();

    // Factual questions about the business itself are answered from the KB.
    // They are not a customer-facing draft waiting on approval.
    if (isBusinessKnowledgeQuestion(ownerAsk)) {
      const kbHits = searchKb(context.kb, question);
      await emitTrace.emit("knowledge_base", {
        description: kbHits.length
          ? `Answered from ${kbHits.length} knowledge-base entr${kbHits.length === 1 ? "y" : "ies"}`
          : "No knowledge-base entry matched this question",
        data: kbHits,
      });
      const answer = await answerFromKnowledge(question, kbHits, runId);
      return {
        orchestratorNotes: [answer],
        noDraftReason: "answered directly from the knowledge base",
      };
    }

    await emitTrace.emit("load_business_profile", {
      description: `Loaded business profile (${presentProfileFields(context.businessProfile).join(", ")})`,
      data: presentProfileFields(context.businessProfile),
    });

    const kbHits = searchKb(context.kb, question);
    const kbHasAnswer = await emitTrace.emit("knowledge_base", {
      description: `Found ${kbHits.length} relevant knowledge-base entr${kbHits.length === 1 ? "y" : "ies"}`,
      data: kbHits,
    });

    const priorChats = searchWidget(context, question);
    await emitTrace.emit("prior_conversations", {
      description: `Found ${priorChats.length} related prior conversation(s)`,
      data: priorChats,
    });

    const businessName = a.field("businessName");
    const signoff = a.signoff();

    // QA fix: when the KB lacks the answer, draft a SAFE HOLDING REPLY (never an
    // internal "I need your business profile" message), and surface the gap to
    // the orchestrator chat separately.
    if (!kbHasAnswer) {
      a.note(
        `Heads up — I don't have anything in your knowledge base about this question, so I drafted a safe holding reply that promises a follow-up rather than inventing an answer. Want to add the details so I can answer directly next time?`,
      );
    }

    const greeting = firstName(customerName)
      ? `Hi ${firstName(customerName)}!`
      : "Hi!";
    const thanks = businessName
      ? `Thanks for reaching out to ${businessName}.`
      : "Thanks for reaching out.";

    const local = (): string => {
      if (kbHasAnswer) {
        return `${greeting} ${thanks} ${extractiveKbAnswer(question, customerFacingSnippets(question, kbHits))}${signoff ? ` — ${signoff}` : ""}`;
      }
      return (
        `${greeting} ${thanks} That's a great question — let me confirm the details on my end ` +
        `and get back to you shortly so I give you the right answer.${signoff ? ` — ${signoff}` : ""}`
      );
    };

    const system =
      `${a.promptBlock()}\n\n` +
      `You draft a short, warm customer-facing reply (1–3 short paragraphs) on the WIDGET channel: ` +
      `plain text only, no markdown. ` +
      greetingInstruction(firstName(customerName)) +
      (kbHasAnswer
        ? `Answer the question using the knowledge-base facts provided; do not invent details.`
        : `You do NOT have the information needed to answer accurately. Write a SAFE HOLDING REPLY that ` +
          `acknowledges the customer, optionally asks one clarifying question, and promises a quick follow-up. ` +
          `Never invent facts. Never expose internal status (do not ask the owner for their profile/KB inside this reply).`) +
      (signoff ? ` Sign off as ${signoff}.` : "");
    const prompt =
      (kbHasAnswer
        ? `Knowledge base:\n${kbHits.map((e) => `- ${e.topic}: ${e.answer}`).join("\n")}\n\n`
        : "") + `Customer question: "${question}"`;

    await emitTrace.work(
      "draft_reply",
      kbHasAnswer
        ? "Answered from the knowledge base"
        : "KB lacks this info — safe holding reply",
    );
    const generated = await generateDraft({ system, prompt, runId, local });
    if (!generated) {
      a.note(
        "Service is temporarily unavailable — please try again in a few minutes.",
      );
      return {
        orchestratorNotes: a.notes,
        noDraftReason: "service temporarily unavailable",
      };
    }

    const topic = deriveTopic(question);
    return {
      draft: {
        title: `Reply to ${customerName ?? "lead"} — ${topic}`,
        body: finishBody("widget_reply", generated.text),
        channel: "widget_reply",
        metadata: {
          topic,
          kb_hit: kbHasAnswer,
          source: generated.source,
          cost_usd: generated.costUsd,
        },
        requiresApproval: true,
      },
      orchestratorNotes: a.notes,
    };
  },
);

function searchWidget(ctx: SharedContext, query: string) {
  const terms = query
    .toLowerCase()
    .split(/\W+/)
    .filter((t) => t.length > 3);
  if (terms.length === 0) return [];
  return ctx.widgetHistory.filter((c) => {
    const hay =
      `${c.summary} ${c.topics.join(" ")} ${c.contactName ?? ""}`.toLowerCase();
    return terms.some((t) => hay.includes(t));
  });
}
