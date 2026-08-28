/**
 * Customer Data & Administration — the department's tool path.
 *
 * This is the first department that can *do* something rather than draft
 * something. When the owner asks to put a note on a customer's record, the
 * department selects the `add_customer_note` tool and hands it to the action
 * executor; the executor decides whether policy allows it, runs it, verifies it,
 * and records it. The department never touches the tool itself.
 *
 * Detection is deliberately conservative. An ask that does not clearly name a
 * customer AND a note falls through to the department's normal drafting skills —
 * a half-understood ask must never turn into a silent write.
 */

import type { DepartmentActionRequest } from "./_department.ts";
import type { SharedContext } from "../types/agent.ts";

/** "add//log/save/put a note ... on|to <customer>'s record" and friends. */
const NOTE_INTENT =
  /\b(add|log|save|attach|put|make|record|jot)\b[^.?!]{0,40}\b(note|comment|remark)\b/i;

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
 * expresses note intent, names a customer that is actually in this tenant's
 * pipeline, and carries note text.
 */
export function resolveRecordAction(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
}): DepartmentActionRequest | undefined {
  const { ownerAsk, params, context } = args;
  if (!NOTE_INTENT.test(ownerAsk)) return undefined;

  const customerName = typeof params.customer_name === "string" ? params.customer_name.trim() : "";
  if (!customerName) return undefined;

  // Only act on a customer this business actually has. Anything else drafts.
  const known = context.pipelineLeads.some((l) =>
    l.name.trim().toLowerCase().startsWith(customerName.toLowerCase()),
  );
  if (!known) return undefined;

  const note = extractNoteText(ownerAsk);
  if (!note) return undefined;

  return {
    toolId: "add_customer_note",
    input: { customer_name: customerName, note },
    describe: (result) => {
      const out = result as { customerName?: string; note?: string; durable?: boolean };
      const where = out.durable === false ? " (this environment stores notes in memory only)" : "";
      return `Added a note to ${out.customerName ?? customerName}'s record: "${out.note ?? note}"${where}.`;
    },
  };
}
