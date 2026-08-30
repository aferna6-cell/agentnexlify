/**
 * Entity resolution — one place that turns a name in an ask into a record.
 *
 * This logic existed in three places with three slightly different answers: the
 * `add_customer_note` tool matched id-then-exact-then-prefix, Sales' skill
 * picker used `name.includes(...)`, and the record action used
 * `startsWith(...)`. Three implementations of "is this the customer they meant"
 * is three chances to disagree, and the disagreement that matters is the one
 * where a substring match quietly picks a person.
 *
 * Every lookup returns a discriminated outcome, so ambiguity is a value the
 * caller must handle rather than a `null` it can mistake for "no match":
 *
 *   exact     one record, matched on a full normalized name
 *   unique    one record, matched on a safe partial (a prefix, or one word)
 *   multiple  several plausible records — the caller MUST ask, never choose
 *   none      nothing matched
 *
 * The pipeline holds both a Mike Johnson and a Mike Rivera. "Email Mike" must
 * return `multiple`. There is no confidence threshold that makes guessing
 * between two real customers acceptable, so none is offered.
 */

import type { AppointmentData, InvoiceData, PipelineLeadData, SharedContext } from "../types/agent.ts";

export type ResolutionKind = "exact" | "unique" | "multiple" | "none";

export type Resolution<T> =
  | { kind: "exact"; match: T }
  | { kind: "unique"; match: T }
  | { kind: "multiple"; matches: T[] }
  | { kind: "none" };

/** True only when exactly one record was identified. */
export function isResolved<T>(r: Resolution<T>): r is { kind: "exact" | "unique"; match: T } {
  return r.kind === "exact" || r.kind === "unique";
}

/** The record if one was identified, else undefined. Never guesses. */
export function resolvedMatch<T>(r: Resolution<T>): T | undefined {
  return isResolved(r) ? r.match : undefined;
}

function normalize(s: string): string {
  return s.trim().toLowerCase().replace(/\s+/g, " ");
}

/**
 * Match `query` against a list by name.
 *
 * Tiers are tried in order and never mixed: an exact match settles it, and the
 * partial tiers only ever run when no exact match existed. Within a tier, more
 * than one candidate is `multiple` — the tier does not fall through to a looser
 * one, because a looser rule cannot break a tie the stricter one could not.
 */
export function resolveByName<T>(items: T[], nameOf: (item: T) => string, query: string): Resolution<T> {
  const q = normalize(query);
  if (!q) return { kind: "none" };

  const exact = items.filter((i) => normalize(nameOf(i)) === q);
  if (exact.length === 1) return { kind: "exact", match: exact[0]! };
  if (exact.length > 1) return { kind: "multiple", matches: exact };

  // A prefix match: "Sarah" for "Sarah Chen". Safe only while unique.
  const prefix = items.filter((i) => normalize(nameOf(i)).startsWith(q));
  if (prefix.length === 1) return { kind: "unique", match: prefix[0]! };
  if (prefix.length > 1) return { kind: "multiple", matches: prefix };

  // A whole-word match anywhere in the name: "Chen" for "Sarah Chen". Word
  // boundaries matter — a bare substring would let "Mike" match "Carmike" and
  // would make short queries dangerous.
  const queryWords = q.split(" ");
  const word = items.filter((i) => {
    const words = normalize(nameOf(i)).split(" ");
    return queryWords.every((qw) => words.includes(qw));
  });
  if (word.length === 1) return { kind: "unique", match: word[0]! };
  if (word.length > 1) return { kind: "multiple", matches: word };

  return { kind: "none" };
}

export function resolveLead(context: SharedContext, query: string): Resolution<PipelineLeadData> {
  return resolveByName(context.pipelineLeads, (l) => l.name, query);
}

export function resolveInvoice(context: SharedContext, query: string): Resolution<InvoiceData> {
  return resolveByName(context.invoices, (i) => i.customerName, query);
}

export function resolveAppointment(context: SharedContext, query: string): Resolution<AppointmentData> {
  return resolveByName(context.appointments, (a) => a.customerName, query);
}

/**
 * Find the customer a request is about, across every place a customer can
 * appear. A person known only from an invoice is still a customer of this
 * business, and refusing to act because they are not in the sales pipeline
 * would be a resolution failure dressed up as caution.
 */
export function resolveCustomerAnywhere(
  context: SharedContext,
  query: string,
): Resolution<{ name: string; leadId?: string }> {
  const names = new Map<string, { name: string; leadId?: string }>();
  for (const l of context.pipelineLeads) names.set(normalize(l.name), { name: l.name, leadId: l.id });
  for (const i of context.invoices) if (!names.has(normalize(i.customerName))) names.set(normalize(i.customerName), { name: i.customerName });
  for (const a of context.appointments) if (!names.has(normalize(a.customerName))) names.set(normalize(a.customerName), { name: a.customerName });
  return resolveByName([...names.values()], (v) => v.name, query);
}

/** A human-readable list of the candidates, for a clarification message. */
export function describeAmbiguity<T>(matches: T[], nameOf: (item: T) => string): string {
  const names = matches.map(nameOf);
  if (names.length <= 2) return names.join(" or ");
  return `${names.slice(0, -1).join(", ")}, or ${names[names.length - 1]}`;
}
