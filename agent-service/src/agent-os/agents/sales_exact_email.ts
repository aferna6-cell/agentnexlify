/**
 * Sales-only: send the owner's exact subject/body when the ask is unambiguous.
 *
 * Current compose (`resolveEmailSendFromOutput`) uses the skill draft. That is
 * correct for "follow up with Sarah" — the agent writes the email. It is wrong
 * for "send exactly this email" when the owner already supplied subject and
 * body: those words must be what gets approved, not a rewritten draft.
 *
 * If the ask is missing a sole recipient, subject, or body — or is not an
 * authorized send — this returns undefined so Sales falls back to compose.
 * Other departments are not wired here.
 */

import type { DepartmentActionRequest } from "./_department.ts";
import type { AskIntent } from "./_intent.ts";
import type { AgentOutput, SharedContext } from "../types/agent.ts";

const EMAIL_RE = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;

function soleRecipient(ask: string): string | undefined {
  const found = [...new Set(ask.match(EMAIL_RE) ?? [])];
  return found.length === 1 ? found[0] : undefined;
}

function extractOwnerSubjectBody(
  ask: string,
): { subject: string; body: string } | undefined {
  const labeled = ask.match(/\bSubject:\s*(.+?)\s*\n\s*Body:\s*([\s\S]+)/i);
  if (labeled) {
    const subject = labeled[1]?.trim() ?? "";
    const body = labeled[2]?.trim() ?? "";
    if (subject && body) return { subject, body };
  }

  // Live smoke (and owners) often use single quotes:
  //   send … with subject 'M8 smoke …' and body 'Milestone 8 …'
  // Double / curly quotes stay valid. Mixed quote styles are still exact.
  const quoted = ask.match(
    /\bwith subject\s+["“'](.+?)["”']\s+and body\s+["“']([\s\S]+?)["”']/i,
  );
  if (quoted) {
    const subject = quoted[1]?.trim() ?? "";
    const body = quoted[2]?.trim() ?? "";
    if (subject && body) return { subject, body };
  }

  return undefined;
}

function describePending(input: Record<string, unknown>): string {
  return (
    `I've written this email to ${input.to} with the subject "${input.subject}". ` +
    "Nothing has been sent — approve it and it goes out from your connected Gmail."
  );
}

function describe(to: string, result: unknown): string {
  const out = result as { to?: string; deduplicated?: boolean } | undefined;
  if (out?.deduplicated) {
    return `That email was already in your mailbox, so I didn't send a second copy to ${to}.`;
  }
  return `Sent the email to ${out?.to ?? to} from your Gmail.`;
}

/**
 * Propose `send_email` with the owner's own subject/body, or undefined so
 * Sales keeps the current compose path.
 */
export function resolveSalesExactEmailFromOutput(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
  output: AgentOutput;
}): DepartmentActionRequest | undefined {
  const { ownerAsk, intent } = args;
  // Permission axis only. Do not use authorizesAction() here: a word in the
  // owner's body ("safe to delete") can classify intent as destroy and would
  // veto a send the owner already wrote out in full.
  if (intent.authorization !== "execute") return undefined;
  if (intent.isQuestion) return undefined;

  const to = soleRecipient(ownerAsk);
  if (!to) return undefined;

  const exact = extractOwnerSubjectBody(ownerAsk);
  if (!exact) return undefined;

  const { subject, body } = exact;
  return {
    toolId: "send_email",
    input: { to, subject, body },
    describePending,
    describe: (result) => describe(to, result),
  };
}
