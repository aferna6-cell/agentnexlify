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

/** Closer that belongs to this opener. Mixed styles are not a pair. */
const QUOTE_CLOSER: Record<string, string> = {
  "'": "'",
  '"': '"',
  "\u201C": "\u201D",
};

function isLetter(ch: string | undefined): boolean {
  return !!ch && /[A-Za-z]/.test(ch);
}

/** Apostrophe between letters (`it's`, `customer's`) is not a quote closer. */
function isInnerApostrophe(
  text: string,
  i: number,
  opener: string,
  closer: string,
): boolean {
  return (
    opener === "'" &&
    closer === "'" &&
    isLetter(text[i - 1]) &&
    isLetter(text[i + 1])
  );
}

/**
 * Subject closer: same delimiter that opened, immediately before `and body`.
 * First-apostrophe + lookahead is not pairing — `'word'` in the subject
 * must not win.
 */
function findSubjectCloser(
  text: string,
  from: number,
  opener: string,
  closer: string,
): number {
  for (let i = from; i < text.length; i++) {
    if (text[i] !== closer) continue;
    if (isInnerApostrophe(text, i, opener, closer)) continue;
    if (/^\s+and body\s+/i.test(text.slice(i + closer.length))) return i;
  }
  return -1;
}

/**
 * Body closer: same delimiter that opened. Take the last paired closer so
 * an inner `'word'` does not truncate the owner body.
 */
function findBodyCloser(
  text: string,
  from: number,
  opener: string,
  closer: string,
): number {
  let last = -1;
  for (let i = from; i < text.length; i++) {
    if (text[i] !== closer) continue;
    if (isInnerApostrophe(text, i, opener, closer)) continue;
    last = i;
  }
  return last;
}

function extractQuotedSubjectBody(
  ask: string,
): { subject: string; body: string } | undefined {
  const head = /\bwith subject\s+/i.exec(ask);
  if (!head || head.index === undefined) return undefined;

  let i = head.index + head[0].length;
  const opener = ask[i] ?? "";
  const closer = QUOTE_CLOSER[opener];
  if (!closer) return undefined;
  i += opener.length;

  const subjectEnd = findSubjectCloser(ask, i, opener, closer);
  if (subjectEnd < 0) return undefined;
  const subject = ask.slice(i, subjectEnd).trim();

  i = subjectEnd + closer.length;
  const mid = /^\s+and body\s+/i.exec(ask.slice(i));
  if (!mid) return undefined;
  i += mid[0].length;

  // Body must open with the same delimiter the subject used.
  if (ask.slice(i, i + opener.length) !== opener) return undefined;
  i += opener.length;

  const bodyEnd = findBodyCloser(ask, i, opener, closer);
  if (bodyEnd < 0) return undefined;
  const body = ask.slice(i, bodyEnd).trim();
  if (!subject || !body) return undefined;
  return { subject, body };
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

  return extractQuotedSubjectBody(ask);
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
