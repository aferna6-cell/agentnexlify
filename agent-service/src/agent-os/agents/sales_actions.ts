/**
 * Sales — proposing a real email send.
 *
 * The department composes the follow-up exactly as it always has, using its
 * existing skills. What changes is what happens next: when the owner named a
 * real recipient address, instead of parking a draft the department proposes a
 * `send_email` action, and the composed text becomes the email the owner
 * approves. Same words, one approval, and the thing that gets approved is the
 * send itself rather than a document that a human then has to copy somewhere.
 *
 * Two rules keep this safe:
 *
 *  1. The recipient must be written in the owner's own ask. An address is
 *     never inferred from the pipeline, never guessed from a name, and never
 *     taken from the composed text — a model that hallucinates an address
 *     cannot cause an email to be proposed to it.
 *  2. Anything short of that falls back to drafting, which is the behaviour
 *     that already existed. Ambiguity produces a draft, never a send.
 */

import type { DepartmentActionRequest } from "./_department.ts";
import type { AgentOutput } from "../types/agent.ts";

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

/** "email/send this to <address>" — an instruction to send, not to draft. */
const SEND_INTENT = /\b(e-?mail|send|shoot|fire off|reach out to)\b/i;

export function wantsSend(ask: string): boolean {
  return SEND_INTENT.test(ask);
}

/**
 * Turn a composed draft into a `send_email` proposal, or return undefined to
 * keep the draft as-is.
 *
 * Runs AFTER the skill composed, so the body the owner approves is the body
 * the agent actually wrote — there is no second generation step between
 * approval and sending.
 */
export function resolveSalesEmailAction(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  output: AgentOutput;
}): DepartmentActionRequest | undefined {
  const { ownerAsk, output } = args;
  if (!wantsSend(ownerAsk)) return undefined;

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
