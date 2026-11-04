/**
 * Plain-English answers for "what can you help me with?" style asks.
 *
 * These ask about the product, not a business department. They used to miss
 * every department and come back as a saved-for-later note. Answer them here
 * instead, in the owner's language.
 */

/**
 * The whole message must be one of these short product questions.
 * A task that merely mentions the words ("list the capabilities of our shop",
 * "what can you do about the overdue invoice") is still a business ask.
 */
const CAPABILITY_RE =
  /^(?:what can you (?:help(?: me with)?|do|handle)|how can you help|what (?:are you able to do|do you do|do you help with)|what are you capable of|what can (?:this|the) (?:ai|assistant|workforce|staff)(?: do| help(?: me with)?| handle)?|show me what you can(?: do)?)[.?!]*$/i;

export function isCapabilityAsk(ask: string): boolean {
  const trimmed = ask.trim();
  if (!trimmed) return false;
  return CAPABILITY_RE.test(trimmed);
}

export function capabilitiesAnswer(): string {
  return [
    "I can help you run the day-to-day work of the business. I draft the words, and you review anything before it is sent.",
    "",
    "Here is what that looks like, with an example you can paste:",
    "",
    '• Follow up with leads — "Draft a friendly follow-up for leads who have not replied."',
    '• Answer a customer — "Reply to the customer asking about our hours."',
    '• Appointments — "Confirm Maria\'s Saturday 10am appointment."',
    '• Marketing — "Draft this week\'s short promotional post."',
    '• Invoices — "Draft a polite reminder for an overdue invoice."',
    '• Weekly summary — "Prepare my weekly business summary."',
    '• Hiring and team notes — "Draft a training checklist for a new hire."',
    '• Documents — "Draft a simple one-page service agreement."',
    "",
    "Tell me the task in everyday language. If I am not sure which part of the business it belongs to, I will ask.",
  ].join("\n");
}
