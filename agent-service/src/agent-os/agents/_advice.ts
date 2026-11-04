/**
 * Practice-advice asks: the owner wants ideas, not a customer message.
 *
 * Department skill choice is keyword scoring plus a default skill. Operations'
 * default is Booking, which always drafts an SMS and, with no slot, asks the
 * customer for a time. An ask such as "give me ideas to reduce late shipments"
 * matches no booking keyword and names no action, so it used to inherit that
 * default. A scored skill, a detected action, or a named deliverable (text,
 * SMS, email, message, reply, post, promo) is left alone — "how can we
 * reduce no-shows? text Jane to confirm 3pm" still drafts, and so does
 * "give me ideas for a promo text".
 *
 * This is a class check, applied only after a department is already chosen,
 * and only when nothing else in that department matches. It does not change
 * classify(), confidence floors, or the routing model.
 */

const GIVE_IDEAS =
  /\b(?:give|show|offer) me\b[\s\S]{0,48}\b(?:ideas?|tips?|suggestions?|advice)\b/i;
const IDEAS_ABOUT =
  /\b(?:ideas?|tips?|suggestions?|advice)\b[\s\S]{0,32}\b(?:to|for|on|about)\b/i;
const WHAT_ARE_TIPS =
  /\bwhat are\b[\s\S]{0,40}\b(?:some |a few |the )?(?:tips?|ideas?|suggestions?|ways)\b/i;
const HOW_IMPROVE =
  /\bhow (?:can|do|should|could) (?:i|we)\b[\s\S]{0,48}\b(?:improve|reduce|increase|cut|lower|boost|prevent|avoid|raise)\b/i;

/** A customer-facing or campaign deliverable named in the ask. Not practice advice. */
const DELIVERABLE =
  /\b(?:texts?|sms|e-?mails?|messages?|replies|reply|posts?|promos?)\b/i;

/** True when the owner named something to draft, even if the sentence also asks for ideas. */
export function namesDeliverable(ask: string): boolean {
  return DELIVERABLE.test(ask);
}

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
 * Generic checklist, not a tailored answer and not a model reply.
 *
 * The same three bullets apply to every topic. Offline routing and CI stay
 * deterministic, and the copy says so instead of presenting the list as a
 * direct take. No customer SMS and no appointment slot.
 */
export function practiceAdviceAnswer(ask: string): string {
  const topic = practiceTopic(ask);
  return [
    `Generic checklist for ${topic} — the same starter list for any question like this, not a tailored answer and not a message to a customer. Nothing was drafted for approval.`,
    "1. Measure the current rate for a short window before changing the process, so you can tell whether a change helped.",
    "2. Find the single step that causes most of the misses and fix that before adding more steps or more people.",
    "3. Put the new rule where the work happens — a cutoff, a checklist, or a visible standard — and review it after one cycle.",
  ].join("\n");
}
