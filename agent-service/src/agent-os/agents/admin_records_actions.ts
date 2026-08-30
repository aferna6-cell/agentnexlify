/**
 * Customer Data & Administration — the department's tool path.
 *
 * Three things decide whether this is an action:
 *  1. intent.intent === "update_record" (or retrieve of the business profile)
 *  2. authorizesAction(intent) — the owner asked for the act, not words
 *  3. the customer resolves to exactly one record (exact/unique), else clarify
 */

import type {
  ClarificationRequest,
  DepartmentActionRequest,
} from "./_department.ts";
import { authorizesAction, readAskIntent, type AskIntent } from "./_intent.ts";
import { describeAmbiguity, resolveCustomerAnywhere } from "./_resolve.ts";
import type { SharedContext } from "../types/agent.ts";

const BUSINESS_PROFILE_RE =
  /\b(my|our|the) (business|company|shop|store)\b|\b(business|company) (name|phone|address|hours|profile|details)\b|\bon file\b/i;

export function extractNoteText(ask: string): string | undefined {
  const marker = ask.match(/\b(?:saying|that says|that|:)\s+(.+)$/i);
  const raw = marker?.[1]?.trim();
  if (!raw) return undefined;
  const cleaned = raw.replace(/^["“']|["”']$/g, "").trim();
  return cleaned.length > 0 ? cleaned : undefined;
}

export function resolveRecordAction(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent?: AskIntent;
}): DepartmentActionRequest | ClarificationRequest | undefined {
  const { ownerAsk, params, context } = args;
  const intent = args.intent ?? readAskIntent(ownerAsk);

  if (intent.intent === "retrieve" && BUSINESS_PROFILE_RE.test(ownerAsk)) {
    return {
      toolId: "get_business_profile",
      input: {},
      describe: (result) => {
        const p = result as Record<string, unknown>;
        const parts = Object.entries(p)
          .filter(([, v]) => typeof v === "string" && v)
          .map(
            ([k, v]) =>
              `${k
                .replace(/([A-Z])/g, " $1")
                .toLowerCase()
                .trim()}: ${String(v)}`,
          );
        return parts.length
          ? `Here's what I have on file — ${parts.join(", ")}.`
          : "I don't have a business profile on file yet.";
      },
    };
  }

  if (intent.intent !== "update_record") return undefined;
  if (!authorizesAction(intent)) return undefined;

  const note = extractNoteText(ownerAsk);
  const customerName =
    typeof params.customer_name === "string" ? params.customer_name.trim() : "";

  if (!customerName) {
    return {
      clarify:
        "I can add that note — which customer's record should it go on? " +
        "Tell me the name and I'll queue it up.",
    };
  }

  const resolution = resolveCustomerAnywhere(context, customerName);

  if (resolution.kind === "multiple") {
    const names = describeAmbiguity(resolution.matches, (m) => m.name);
    return {
      clarify: `I found more than one customer matching "${customerName}" — ${names}. Which one did you mean?`,
    };
  }

  if (resolution.kind === "none") return undefined;

  if (!note) {
    return {
      clarify: `What should the note on ${resolution.match.name}'s record say?`,
    };
  }

  return {
    toolId: "add_customer_note",
    input: { customer_name: resolution.match.name, note },
    describe: (result) => {
      const out = result as {
        customerName?: string;
        note?: string;
        durable?: boolean;
      };
      const where =
        out.durable === false
          ? " (this environment stores notes in memory only)"
          : "";
      return `Added a note to ${out.customerName ?? resolution.match.name}'s record: "${out.note ?? note}"${where}.`;
    },
  };
}
