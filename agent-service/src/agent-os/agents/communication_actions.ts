/**
 * Communication actions — propose a send, or ask instead of guessing.
 *
 * Shared by departments that write to customers. Proposal is capability-gated
 * (`canProposeSendEmail`); clarification is available to every eligible
 * communication department even when sending is off.
 *
 * Two rules keep a send safe:
 *  1. The recipient address must appear in the owner's own ask. Never inferred
 *     from the pipeline, a name, or model-composed text.
 *  2. The owner must have authorized an act (`authorizesAction`), not asked
 *     for words. "Draft an email to Sarah" never becomes a send.
 */

import type {
  ClarificationRequest,
  DepartmentActionRequest,
} from "./_department.ts";
import { authorizesAction, type AskIntent } from "./_intent.ts";
import { describeAmbiguity, resolveCustomerAnywhere } from "./_resolve.ts";
import {
  canProposeSendEmail,
  isCommunicationEligible,
} from "./communication_capabilities.ts";
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

/**
 * Ask when a communication names one person/object the system cannot pin down.
 * Safe with the flag off: it never proposes a send.
 */
export function resolveCommunicationAmbiguity(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
  departmentId?: string;
}): DepartmentActionRequest | ClarificationRequest | undefined {
  const { ownerAsk, params, context, intent, departmentId } = args;
  if (
    departmentId &&
    !isCommunicationEligible(departmentId) &&
    departmentId !== "sales"
  ) {
    return undefined;
  }
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

/**
 * Turn a composed draft into a send_email proposal, or keep the draft.
 * Capability-gated: default Sales only, and SEND_EMAIL_ENABLED must be on.
 */
export function resolveEmailSendFromOutput(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
  output: AgentOutput;
  departmentId: string;
}): DepartmentActionRequest | undefined {
  const { ownerAsk, intent, output, departmentId } = args;

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
