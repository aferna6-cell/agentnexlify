/**
 * Task intent — what the owner wants DONE, separated from what it is done TO.
 *
 * The decision pipeline used to have only one semantic axis: business-subject
 * keywords. "quote" scored Sales, "invoice" scored Invoicing, "note" scored
 * nothing at all. That single axis cannot tell these apart:
 *
 *   "Create a quote for Dana"          → make a new business object
 *   "Email Dana about her existing quote" → communicate about one that exists
 *
 * Both are about a quote. Only one of them should ever reach a quote generator,
 * and the other must be able to become a send. Collapsing them is what made a
 * communication request die inside `quote_generator` with "no line items
 * provided", and what made record-mutation requests route to whichever
 * department happened to own a noun in the sentence.
 *
 * So an ask is parsed onto four independent axes:
 *
 *   intent         what to do            communicate / create / update_record / …
 *   subjectType    what it is about      quote / invoice / appointment / …
 *   channel        how it goes out       email / sms / none
 *   authorization  who performs it       execute / draft_only / ambiguous
 *
 * `authorization` is deliberately its own axis rather than a property of the
 * verb. "Draft an email to Sarah" and "Email Sarah" share an intent and a
 * channel; they differ only in who presses send. That is a permission question,
 * and permission questions belong next to the approval model, not inside a
 * keyword list.
 *
 * This module is pure: string in, structure out. No I/O, no context, no model.
 * It is a lens, not a decision — every consumer decides for itself what to do
 * with what it sees, and an `unknown` intent must always be safe to receive.
 */

/** What the owner wants performed. */
export type TaskIntent =
  | "communicate"
  | "create"
  | "update_record"
  | "retrieve"
  | "schedule"
  | "analyze"
  | "destroy"
  | "unknown";

/** What the task is performed on. */
export type SubjectType =
  | "quote"
  | "invoice"
  | "appointment"
  | "customer_record"
  | "review"
  | "complaint"
  | "document"
  | "campaign"
  | "staff"
  | "finances"
  /**
   * A message the business is answering. Replying is a different task from
   * initiating, and they belong to different departments: Customer Service
   * answers what came in, everyone else starts the conversation. Collapsing
   * both into one "message" subject made Customer Service the destination for
   * every outbound email that mentioned no other business object.
   */
  | "inbound_message"
  /** A message the business is sending first. */
  | "outbound_message"
  | "none";

export type IntentChannel = "email" | "sms" | "phone" | "none";

/**
 * Who is authorized to perform the task.
 *
 * `draft_only` is the conservative answer and wins every tie: an owner who
 * asked for words is never surprised by a send, whereas an owner who asked for
 * a send and got words has lost nothing but a click.
 */
export type Authorization = "execute" | "draft_only" | "ambiguous";

export interface AskIntent {
  intent: TaskIntent;
  subjectType: SubjectType;
  channel: IntentChannel;
  authorization: Authorization;
  /** The subject is an object that already exists, not one to be made. */
  subjectExists: boolean;
  /** The ask is phrased as a question about practice, not an instruction. */
  isQuestion: boolean;
}

// --- Authorization ---------------------------------------------------------

/**
 * Phrasings that ask for words rather than for an act. Deliberately broad: a
 * false "draft_only" costs one click, a false "execute" sends real mail.
 */
const DRAFT_MARKERS = [
  /\b(draft|compose|write)\b/i,
  /\b(give|show|send) me (some |the )?(wording|copy|text|something|a draft)\b/i,
  /\b(put together|rough out|sketch out|work up)\b/i,
  /\bwhat would you (say|write|send)\b/i,
  /\bhow (would|should) (i|we) (say|word|phrase|put)\b/i,
  /\bsomething i (can|could)\b/i,
  /\bso i can (send|review|look)\b/i,
  /\bi'?ll (look|review|check|read) (it |them )?over\b/i,
  /\bbefore (i|we) send\b/i,
  /\bfor (me|my) (to )?(review|approval)\b/i,
  /\bdon'?t send\b/i,
];

/** Phrasings that instruct the system to actually carry the task out. */
const EXECUTE_MARKERS = [
  /\b(e-?mail|text|message|send|shoot|fire off)\b/i,
  /\b(add|log|record|save|attach|put|jot|note)\b/i,
  /\b(go ahead and|please)\b/i,
];

function readAuthorization(ask: string): Authorization {
  const wantsWords = DRAFT_MARKERS.some((re) => re.test(ask));
  const wantsAct = EXECUTE_MARKERS.some((re) => re.test(ask));

  // Asking for words wins outright, even alongside a send verb: "write me
  // something I can send to Sarah" names a send and still authorizes nothing.
  if (wantsWords) return "draft_only";
  if (wantsAct) return "execute";
  // "Follow up with Sarah." — a real task, no stated channel and no stated
  // permission. Neither drafting nor sending is obviously wrong, so say so
  // rather than pick one silently.
  return "ambiguous";
}

// --- Intent ----------------------------------------------------------------

const COMMUNICATE_RE =
  /\b(e-?mails?|texts?|sms|messages?|call|repl(y|ies)|respond|response|answer|notify|tell|send|sends|sending|shoot|fire off|forward|let (him|her|them|\w+) know|follow[- ]?up|follow up|check in|chase|circle back|nudge|touch base|reach out|get back to|apolog(y|ise|ize)|thank)\b/i;
const CREATE_RE =
  /\b(create|generate|make|build|draft|write|compose|prepare|put together|rough out|work up|come up with)\b/i;
const UPDATE_RECORD_RE =
  /\b(note|notes|noting|log|logged|record|records|recording|mark|flag|save|attach|jot|update|add)\b/i;
const RETRIEVE_RE =
  /\b(what'?s?|which|who|show|list|pull up|look up|find|how many|how much|do (i|we) have|on file)\b/i;
const SCHEDULE_RE =
  /\b(book|schedule|reschedule|cancel|move|slot|appointment|calendar)\b/i;
const ANALYZE_RE =
  /\b(why|analy[sz]e|figure out|explain|breakdown|break down|trend|compare|should (i|we))\b/i;
const DESTROY_RE = /\b(delete|remove|purge|wipe|erase|drop|get rid of)\b/i;

/** Objects that make a "draft/write" ask a message rather than a new artifact. */
const MESSAGE_OBJECT_RE =
  /\b(e-?mail|message|text|note to|reply|response|apology|thank[- ]you|follow[- ]?up|reminder|wording|copy)\b/i;

/** The record-mutation shape: a note/flag placed ON a customer's record. */
const RECORD_TARGET_RE = /\b(record|file|account|profile|crm|notes?)\b/i;

function readIntent(
  ask: string,
  subject: SubjectType,
  isQuestion: boolean,
  subjectExists: boolean,
): TaskIntent {
  // Destruction first: it is the one intent whose misreading is unrecoverable.
  if (DESTROY_RE.test(ask)) return "destroy";

  // A note/flag placed on a customer's record is a record mutation, whatever
  // noun the note happens to mention. This is what makes "note on Mike's record
  // that he approved the tire quote" a record update rather than a quote task.
  if (UPDATE_RECORD_RE.test(ask) && RECORD_TARGET_RE.test(ask) && !isQuestion) {
    return "update_record";
  }

  // A question about practice ("should I be noting…") is analysis, never the
  // act it describes. This is the hard-negative half of every action pair.
  //
  // But "what would you say to Sarah to tell her the car is ready?" is an
  // imperative in question clothing: the owner wants the words, not a fact
  // about the business. Treating every question mark as a retrieval sent those
  // requests to departments that answer questions instead of the one that
  // writes the message. The draft markers already know the difference, so the
  // question form only decides AUTHORIZATION, never the task itself.
  if (isQuestion && !DRAFT_MARKERS.some((re) => re.test(ask))) {
    if (ANALYZE_RE.test(ask)) return "analyze";
    return "retrieve";
  }

  if (SCHEDULE_RE.test(ask) && !COMMUNICATE_RE.test(ask)) return "schedule";

  // Communication outranks creation when the object of the verb is a message:
  // "draft an email" is communicating (with draft authorization), not creating
  // a business object. "Draft a quote" is creating one.
  if (COMMUNICATE_RE.test(ask)) {
    if (
      CREATE_RE.test(ask) &&
      !MESSAGE_OBJECT_RE.test(ask) &&
      // You do not create a thing that already exists. "Write me something I
      // can send to Sarah about the brake quote" carries a create verb and a
      // quote, and is not a request to produce a quote.
      !subjectExists &&
      subject !== "none" &&
      subject !== "inbound_message" &&
      subject !== "outbound_message"
    ) {
      return "create";
    }
    return "communicate";
  }

  // Creation requires something that does not yet exist. An ask that refers to
  // an existing object is about that object, not a request to make another.
  if (CREATE_RE.test(ask)) return subjectExists ? "communicate" : "create";
  if (ANALYZE_RE.test(ask)) return "analyze";
  if (RETRIEVE_RE.test(ask)) return "retrieve";
  return "unknown";
}

// --- Subject ---------------------------------------------------------------

/**
 * Ordered most-specific first. The first hit wins, so a sentence mentioning
 * both a complaint and an invoice is read as the complaint — the more urgent
 * and more constrained reading.
 */
const SUBJECT_PATTERNS: [SubjectType, RegExp][] = [
  [
    "complaint",
    /\b(complaints?|complained|furious|angry|upset|unhappy|apolog(y|ise|ize)|went wrong|ruined|damaged)\b/i,
  ],
  ["review", /\b(reviews?|testimonials?|google review|yelp|star rating)\b/i],
  [
    "invoice",
    /\b(invoices?|bills?|billing|past due|overdue|payments?|owes?|balance|refunds?)\b/i,
  ],
  ["quote", /\b(quotes?|quotation|estimates?|proposals?)\b/i],
  // "the car is ready" is service completion — the same operational subject as
  // "ready for pickup", which is why both halves of a hard-negative pair that
  // differ only in phrasing must land in the same department.
  [
    "appointment",
    /\b(appointments?|bookings?|slots?|reschedul|visits?|drop[- ]?offs?|pick[- ]?ups?|(is|are)\s+ready|ready for pick)\b/i,
  ],
  // Checked before customer_record: "email everyone in the pipeline a discount
  // offer" is a campaign that happens to name the pipeline, not a records task.
  [
    "campaign",
    /\b(campaigns?|newsletters?|blast|promo|specials?|discounts?|offers?|social post|facebook|instagram|blog)\b/i,
  ],
  [
    "customer_record",
    /\b(records?|files?|profiles?|crm|customer data|pipeline)\b/i,
  ],
  [
    "staff",
    /\b(employees?|staff|hire|hiring|payroll|job posts?|training|handbook|team member)\b/i,
  ],
  [
    "finances",
    /\b(revenue|financial|profit|cash flow|receivables|taxes?|quarterly|bookkeep)\b/i,
  ],
  [
    "document",
    /\b(contracts?|agreements?|intake forms?|sop|polic(y|ies)|one[- ]?pagers?|templates?|checklists?)\b/i,
  ],
  // Direction is decided below; the entry itself only detects "this is about a
  // message".
  [
    "outbound_message",
    /\b(e-?mails?|messages?|texts?|repl(y|ies)|respond(ing)?|responses?|wording|note to)\b/i,
  ],
];

/** The business is answering something that came to it. */
const INBOUND_RE =
  /\b(reply|replies|respond|response|answer|got back to|wrote in|came in|asked|inquiry|enquiry|question|they said|customer said)\b/i;

function readSubject(ask: string): SubjectType {
  for (const [subject, re] of SUBJECT_PATTERNS) {
    if (!re.test(ask)) continue;
    if (subject === "outbound_message") {
      return INBOUND_RE.test(ask) ? "inbound_message" : "outbound_message";
    }
    return subject;
  }
  return "none";
}

// --- Channel ---------------------------------------------------------------

function readChannel(ask: string): IntentChannel {
  if (/\b(e-?mail|inbox|cc|bcc)\b/i.test(ask)) return "email";
  if (/\b(text|sms|txt)\b/i.test(ask)) return "sms";
  if (/\b(call|phone|ring)\b/i.test(ask)) return "phone";
  return "none";
}

// --- Existing-subject detection -------------------------------------------

/**
 * Does the ask refer to an object that already exists?
 *
 * This is what stops "follow up on the quote we sent her" from being read as a
 * request to produce a new quote. It is the single most load-bearing signal for
 * keeping communication requests out of generative skills.
 */
const EXISTING_RE = [
  /\b(that|the|her|his|their|this)\b[^.?!]{0,40}\b(we (sent|gave|quoted|issued|wrote)|already|existing|outstanding|open|previous|last)\b/i,
  // "…about the brake quote" — you can only write ABOUT something that exists.
  // This is the sentence-level form of the subject/task split: the quote is
  // what the message is about, not the thing being produced.
  /\babout (the|that|this|her|his|their)\s+\w+/i,
  /\bstill (wants?|interested|needs?)\b/i,
  /\b(his|her|their|the) (existing|outstanding|open|current|last)\b/i,
  /\b(follow[- ]?up|check in|chase|circle back|nudge|touch base|remind)\b/i,
  /\bwe (sent|quoted|gave|issued)\b/i,
];

function readSubjectExists(ask: string): boolean {
  return EXISTING_RE.some((re) => re.test(ask));
}

// --- Entry point -----------------------------------------------------------

const QUESTION_RE =
  /^\s*(what|which|who|when|where|why|how|should|can|could|do|does|did|is|are|am)\b/i;

/**
 * Parse a request onto the four semantic axes.
 *
 * `canAuthorizeActions` is false for customer-authored inbound messages. Their
 * words may describe a task, but they can never grant owner authority.
 */
export function readAskIntent(
  ask: string,
  canAuthorizeActions = true,
): AskIntent {
  const isQuestion =
    QUESTION_RE.test(ask) ||
    (ask.trim().endsWith("?") && !/^\s*(please|go ahead)/i.test(ask));
  const subjectType = readSubject(ask);
  const subjectExists = readSubjectExists(ask);
  const intent = readIntent(ask, subjectType, isQuestion, subjectExists);
  return {
    intent,
    subjectType,
    channel: readChannel(ask),
    // A question is never an instruction to act, whatever verbs it contains.
    authorization:
      isQuestion || !canAuthorizeActions
        ? "draft_only"
        : readAuthorization(ask),
    subjectExists,
    isQuestion,
  };
}

/**
 * Is this ask eligible to become an executable action at all?
 *
 * The gate every action path consults before proposing anything. It answers a
 * permission question, not a capability question: a `false` here means the
 * owner did not authorize an act, regardless of whether a tool exists for it.
 */
export function authorizesAction(intent: AskIntent): boolean {
  if (intent.authorization !== "execute") return false;
  // Destruction and analysis never become actions in this system: there is no
  // tool behind them, and inventing one from a verb is exactly the failure mode
  // the approval model exists to prevent.
  return (
    intent.intent !== "destroy" &&
    intent.intent !== "analyze" &&
    intent.intent !== "unknown"
  );
}
