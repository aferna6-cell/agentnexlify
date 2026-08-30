/**
 * Communication actions — proposing a real send, and refusing to guess who it
 * is for.
 *
 * Capability, not department wording, decides whether a send may be proposed.
 * `canProposeSendEmail(departmentId)` is the same gate policy uses:
 * SEND_EMAIL_ENABLED defaults off, and only departments in
 * SEND_EMAIL_PROPOSE_DEPARTMENTS (Sales, this milestone) may propose.
 *
 * Two decisions live here, at different points:
 *
 * BEFORE composing (`resolveCommunicationAmbiguity`): can this communication
 * be completed at all? A bare "him", or a "Mike" when the pipeline holds two,
 * has no safe continuation. Drafting to nobody is not one. So it asks — but
 * only when a send could actually follow. Flag-off / non-Sales drafts.
 *
 * AFTER composing (`resolveEmailSendFromOutput`): should the composed text be
 * sent rather than handed over? The composed body becomes the email the owner
 * approves. Never proposed unless the capability gate allows it.
 *
 * Two rules keep the send safe:
 *
 *  1. The recipient address must be written in the owner's own ask. An address
 *     is never inferred from the pipeline, never guessed from a name, and never
 *     taken from the composed text.
 *  2. The owner must have authorized an act (`authorizesAction`). "Write me
 *     something I can send to Sarah" names a send and authorizes nothing.
 */

import type {
  ClarificationRequest,
  DepartmentActionRequest,
} from "./_department.ts";
import { authorizesAction, type AskIntent } from "./_intent.ts";
import { describeAmbiguity, resolveCustomerAnywhere } from "./_resolve.ts";
import { canProposeSendEmail } from "../capabilities/send_email.ts";
import type { AgentOutput, SharedContext } from "../types/agent.ts";

const EMAIL_RE = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;

export function soleRecipient(ask: string): string | undefined {
  const found = [...new Set(ask.match(EMAIL_RE) ?? [])];
  return found.length === 1 ? found[0] : undefined;
}

const DANGLING_PRONOUN_RE =
  /\b(him|her|them|that customer|that guy|that lady|the customer)\b/i;
const DEFINITE_OBJECT_RE =
  /\b(the|that|this)\s+(quote|estimate|invoice|bill)\b/i;
const GROUP_RE =
  /\b(everyone|all|customers|leads|people|three|two|several|each|both)\b/i;

export function resolveCommunicationAmbiguity(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
  departmentId?: string;
}): DepartmentActionRequest | ClarificationRequest | undefined {
  const { ownerAsk, params, context, intent, departmentId } = args;
  // Only interrogate the owner when a send could actually follow.
  if (!canProposeSendEmail(departmentId)) return undefined;
  if (intent.intent !== "communicate") return undefined;
  if (intent.authorization === "draft_only") return undefined;
  if (GROUP_RE.test(ownerAsk)) return undefined;
  if (soleRecipient(ownerAsk)) return undefined;

  const named =
    typeof params.customer_name === "string" ? params.customer_name.trim() : "";

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

  if (DANGLING_PRONOUN_RE.test(ownerAsk)) {
    return {
      clarify:
        "Who should this go to? I don't want to guess which customer you mean.",
    };
  }

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

export function resolveEmailSendFromOutput(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
  output: AgentOutput;
  departmentId: string;
}): DepartmentActionRequest | undefined {
  const { ownerAsk, intent, output, departmentId } = args;

  // Never propose what policy will refuse: the owner should see a draft, not a
  // denial that explains an internal gate.
  if (!canProposeSendEmail(departmentId)) return undefined;
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
