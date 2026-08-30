/**
 * Customer Data & Administration — the department's tool path.
 *
 * When the owner asks to put a note on a customer's record, the department
 * selects the `add_customer_note` tool and hands it to the action executor; the
 * executor decides whether policy allows it, runs it, verifies it, and records
 * it. The department never touches the tool itself.
 *
 * Three things decide whether this is an action, and all three are general:
 *
 *  1. `intent.intent === "update_record"` — the ask is a record mutation, read
 *     off the task axis rather than off the presence of the word "note". This
 *     is what distinguishes "note on Mike's record that he approved the quote"
 *     (act) from "should I be noting quote approvals?" (a question about
 *     practice, which must never write anything).
 *  2. `authorizesAction(intent)` — the owner asked for it to be done, not for
 *     words about doing it.
 *  3. The customer resolves to exactly one record in this tenant's data.
 *
 * Where the customer is named but ambiguous, this asks. That is a third outcome
 * beside acting and drafting, and it is the right one: two customers called
 * Mike is not a reason to draft, and certainly not a reason to pick one.
 */

import type {
  ClarificationRequest,
  DepartmentActionRequest,
} from "./_department.ts";
import { authorizesAction, type AskIntent } from "./_intent.ts";
import { describeAmbiguity, resolveLead } from "./_resolve.ts";
import type { SharedContext } from "../types/agent.ts";

/** The business's own details, as distinct from a customer's. */
const BUSINESS_PROFILE_RE =
  /\b(my|our|the) (business|company|shop|store)\b|\b(business|company) (name|phone|address|hours|profile|details)\b/i;

/**
 * Pull the note text out of the ask. Owners phrase this as "… saying X",
 * "… that X", or "…: X". Everything after the marker is the note.
 */
export function extractNoteText(ask: string): string | undefined {
  const marker = ask.match(/\b(?:saying|that says|that|:)\s+(.+)$/i);
  const raw = marker?.[1]?.trim();
  if (!raw) return undefined;
  const cleaned = raw.replace(/^["“']|["”']$/g, "").trim();
  return cleaned.length > 0 ? cleaned : undefined;
}

/**
 * Decide whether this ask is a "note on a record" action.
 *
 * Returns undefined — meaning "not an action, draft instead" — unless the ask
 * is a record mutation the owner authorized, against a customer this business
 * actually has, with note text to store.
 */
export function resolveRecordAction(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
}): DepartmentActionRequest | ClarificationRequest | undefined {
  const { ownerAsk, params, context, intent } = args;

  // Reading the business's own profile is a level-0 tool call, not a document
  // to draft. Asking "what's my phone number on file?" and being handed a
  // freshly written one-pager is the same category error as answering a
  // communication request with a quote generator: the department reached for
  // the skill it usually uses instead of the capability the task named.
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

  // Nothing to identify the customer by. Ask rather than draft a note into the
  // void — the owner plainly wants a record updated, they just did not say whose.
  if (!customerName) {
    return {
      clarify:
        "I can add that note — which customer's record should it go on? " +
        "Tell me the name and I'll queue it up.",
    };
  }

  const resolution = resolveLead(context, customerName);

  // Two customers match. There is no safe way to choose, so do not.
  if (resolution.kind === "multiple") {
    const names = describeAmbiguity(resolution.matches, (m) => m.name);
    return {
      clarify: `I found more than one customer matching "${customerName}" — ${names}. Which one did you mean?`,
    };
  }

  // Not a customer of this business. Fall through to drafting rather than
  // inventing a record.
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
