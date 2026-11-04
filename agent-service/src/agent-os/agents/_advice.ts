/**
 * Practice-advice asks: the owner wants ideas, not a customer message.
 *
 * Department skill choice is keyword scoring plus a default skill. Operations'
 * default is Booking, which always drafts an SMS and, with no slot, asks the
 * customer for a time. An ask such as "give me ideas to reduce late shipments"
 * matches no booking keyword, so it used to inherit that default. The same
 * class also trips incidental keywords ("late" → HR memo, "book" inside
 * "booking show rate" → Booking). Those are advice, not instructions to draft
 * or to act.
 *
 * This is a class check, applied only after a department is already chosen.
 * It does not change classify(), confidence floors, or the routing model.
 */

const GIVE_IDEAS =
  /\b(?:give|show|offer) me\b[\s\S]{0,48}\b(?:ideas?|tips?|suggestions?|advice)\b/i;
const IDEAS_ABOUT =
  /\b(?:ideas?|tips?|suggestions?|advice)\b[\s\S]{0,32}\b(?:to|for|on|about)\b/i;
const WHAT_ARE_TIPS =
  /\bwhat are\b[\s\S]{0,40}\b(?:some |a few |the )?(?:tips?|ideas?|suggestions?|ways)\b/i;
const HOW_IMPROVE =
  /\bhow (?:can|do|should|could) (?:i|we)\b[\s\S]{0,48}\b(?:improve|reduce|increase|cut|lower|boost|prevent|avoid|raise)\b/i;

/** True when the owner is asking for practice advice rather than a draft or an action. */
export function isPracticeAdviceAsk(ask: string): boolean {
  return (
    GIVE_IDEAS.test(ask) ||
    IDEAS_ABOUT.test(ask) ||
    WHAT_ARE_TIPS.test(ask) ||
    HOW_IMPROVE.test(ask)
  );
}

function practiceTopic(ask: string): string {
  const trimmed = ask.trim().replace(/[.?!]+$/, "");
  const patterns = [
    /\b(?:ideas?|tips?|suggestions?|advice)\s+(?:to|for|on|about)\s+(.+)$/i,
    /\bhow (?:can|do|should|could) (?:i|we)\s+(.+)$/i,
    /\bwhat are\s+(?:some |a few |the )?(?:tips?|ideas?|suggestions?|ways)\s+(?:to|for|on|about)\s+(.+)$/i,
  ];
  for (const re of patterns) {
    const match = trimmed.match(re);
    const topic = match?.[1]?.trim();
    if (topic) return topic;
  }
  return trimmed;
}

/**
 * A plain answer for the owner. No customer SMS, no appointment slot, no draft.
 * Deterministic so offline routing and CI do not depend on a model.
 */
export function practiceAdviceAnswer(ask: string): string {
  const topic = practiceTopic(ask);
  return [
    `Here's a direct take on ${topic}. This is advice for you, not a message to a customer, so nothing was drafted for approval.`,
    "1. Measure the current rate for a short window before changing the process, so you can tell whether a change helped.",
    "2. Find the single step that causes most of the misses and fix that before adding more steps or more people.",
    "3. Put the new rule where the work happens — a cutoff, a checklist, or a visible standard — and review it after one cycle.",
  ].join("\n");
}
