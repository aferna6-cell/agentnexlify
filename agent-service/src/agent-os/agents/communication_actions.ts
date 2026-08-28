/**
 * Communication actions — proposing a real send, and refusing to guess who it
 * is for. Shared by every department that talks to customers.
 *
 * This started life as Sales-only wiring, and that was the bug: Operations
 * would compose a perfect "your car is ready" message to an address the owner
 * had written out in full, and then hand it back as a draft, because the
 * ability to propose a send was a property of one department rather than of the
 * system. Whether a message can be sent depends on the message and the owner's
 * authorization — not on which department happened to write it.
 *
 * Two decisions live here, and they run at different points for a reason.
 *
 * BEFORE composing (`resolveSalesCommunication`): can this communication be
 * completed at all? An ask that names a recipient the system cannot pin down —
 * a bare "him", or a "Mike" when the pipeline holds two — has no safe
 * continuation. Drafting is not a safe continuation either: a follow-up written
 * to nobody wastes the owner's attention, and one written to the wrong Mike is
 * worse. So it asks.
 *
 * AFTER composing (`resolveSalesEmailAction`): should the composed text be
 * sent rather than handed over? The composed body becomes the email the owner
 * approves, so what gets approved is exactly what was written — there is no
 * second generation step between approval and sending.
 *
 * Two rules keep the send safe:
 *
 *  1. The recipient address must be written in the owner's own ask. An address
 *     is never inferred from the pipeline, never guessed from a name, and never
 *     taken from the composed text — a model that hallucinates an address
 *     cannot cause an email to be proposed to it.
 *  2. The owner must have authorized an act rather than asked for words. That
 *     is `authorizesAction`, which reads the permission axis of the ask instead
 *     of pattern-matching a send verb. "Write me something I can send to
 *     Sarah" names a send and authorizes nothing, and this is the single rule
 *     that keeps every hard-negative pair on the right side of the line.
 */

import type { ClarificationRequest, DepartmentActionRequest } from "./_department.ts";
import { authorizesAction, type AskIntent } from "./_intent.ts";
import { describeAmbiguity, resolveCustomerAnywhere } from "./_resolve.ts";
import type { AgentOutput, SharedContext } from "../types/agent.ts";

/**
 * A single address written in the ask. Deliberately strict, and deliberately
 * refuses when there is more than one: "email a@x.com and b@y.com" is exactly
 * the case where guessing which one the owner meant is unacceptable.
 */
const EMAIL_RE = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;

export function soleRecipient(ask: string): string | undefined {
  const found = [...new Set(ask.match(EMAIL_RE) ?? [])];
  return found.length === 1 ? found[0] : undefined;
}

/** A pronoun standing in for a person the ask never named. */
const DANGLING_PRONOUN_RE = /\b(him|her|them|that customer|that guy|that lady|the customer)\b/i;

/** A definite reference to one business object: "the quote", "that invoice". */
const DEFINITE_OBJECT_RE = /\b(the|that|this)\s+(quote|estimate|invoice|bill)\b/i;

/** A plural or group reference, which is not an ambiguity to resolve. */
const GROUP_RE = /\b(everyone|all|customers|leads|people|three|two|several|each|both)\b/i;

/**
 * Decide whether a communication request is under-specified in a way that can
 * only be settled by the owner. Used by every department that writes to a
 * customer.
 *
 * Runs before composition. Returns a question when the ask points at one
 * specific person or object and the system cannot tell which, and undefined in
 * every other case — including group asks, which are not ambiguous at all.
 */
export function resolveCommunicationAmbiguity(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
}): DepartmentActionRequest | ClarificationRequest | undefined {
  const { ownerAsk, params, context, intent } = args;
  if (intent.intent !== "communicate") return undefined;
  // Ambiguity is only worth a question when something will actually happen to
  // the person. An owner who asked for words gets words: writing a generic
  // apology costs nothing if the wrong customer is imagined, whereas sending
  // one does. Asking here would interrogate the owner about a draft.
  if (intent.authorization === "draft_only") return undefined;
  // A group ask ("reach out to the three customers we haven't seen") names no
  // individual, so there is nothing to disambiguate.
  if (GROUP_RE.test(ownerAsk)) return undefined;
  // An address in the ask settles the recipient regardless of names.
  if (soleRecipient(ownerAsk)) return undefined;

  const named = typeof params.customer_name === "string" ? params.customer_name.trim() : "";

  if (named) {
    const resolution = resolveCustomerAnywhere(context, named);
    if (resolution.kind === "multiple") {
      const names = describeAmbiguity(resolution.matches, (m) => m.name);
      return {
        clarify: `More than one customer matches "${named}" — ${names}. Which one should I write to?`,
      };
    }
    return undefined;
  }

  // No name at all, but the ask points at a particular person.
  if (DANGLING_PRONOUN_RE.test(ownerAsk)) {
    return { clarify: "Who should this go to? I don't want to guess which customer you mean." };
  }

  // "Follow up on the quote" — which quote? Only a question when the business
  // actually has more than one candidate; with a single open quote there is
  // nothing ambiguous about it.
  if (DEFINITE_OBJECT_RE.test(ownerAsk)) {
    const isInvoice = /\b(invoice|bill)\b/i.test(ownerAsk);
    const candidates = isInvoice
      ? context.invoices.map((i) => i.customerName)
      : context.pipelineLeads.filter((l) => l.quoteAmount).map((l) => l.name);
    if (candidates.length > 1) {
      return {
        clarify: `Which ${isInvoice ? "invoice" : "quote"} do you mean? I have open ones for ${describeAmbiguity(candidates.slice(0, 4), (n) => n)}.`,
      };
    }
  }

  return undefined;
}

/**
 * Turn a composed draft into a `send_email` proposal, or return undefined to
 * keep the draft as-is.
 */
export function resolveEmailSendFromOutput(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
  output: AgentOutput;
}): DepartmentActionRequest | undefined {
  const { ownerAsk, intent, output } = args;

  // The permission axis, not a verb list. An ask for words never becomes a send
  // however many send verbs it contains.
  if (!authorizesAction(intent)) return undefined;
  if (intent.intent !== "communicate") return undefined;
  if (intent.channel !== "email") return undefined;

  const to = soleRecipient(ownerAsk);
  if (!to) return undefined;

  const draft = output.draft;
  if (!draft) return undefined;

  const subject = draft.title?.trim();
  const body = draft.body?.trim();
  if (!subject || !body) return undefined;

  return {
    toolId: "send_email",
    input: { to, subject, body },
    describePending: (input) =>
      `I've written this email to ${input.to} with the subject "${input.subject}". ` +
      "Nothing has been sent — approve it and it goes out from your connected Gmail.",
    describe: (result) => {
      const out = result as { to?: string; deduplicated?: boolean } | undefined;
      if (out?.deduplicated) {
        return `That email was already in your mailbox, so I didn't send a second copy to ${to}.`;
      }
      return `Sent the email to ${out?.to ?? to} from your Gmail.`;
    },
  };
}
