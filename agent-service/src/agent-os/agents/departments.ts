/**
 * The 8 department heads (Agent Library v2). Each bundles v1 worker agents as
 * internal skills; see docs/AgentNexLiFy_Agent_Library_v2.md.
 */

import { defineDepartment } from "./_department.ts";
import { resolveRecordAction } from "./admin_records_actions.ts";
import { resolveCommunicationAmbiguity, resolveEmailSendFromOutput } from "./communication_actions.ts";

// v1 worker agents, now used as internal skills.
import { booking } from "./booking/agent.ts";
import { appointmentReminder } from "./appointment_reminder/agent.ts";
import { customerQuestion } from "./customer_question/agent.ts";
import { complaintHandler } from "./complaint_handler/agent.ts";
import { leadNurture } from "./lead_nurture/agent.ts";
import { quoteFollowUp } from "./quote_follow_up/agent.ts";
import { quoteGenerator } from "./quote_generator/agent.ts";
import { outreach } from "./outreach/agent.ts";
import { campaign } from "./campaign/agent.ts";
import { contentWriter } from "./content_writer/agent.ts";
import { socialPost } from "./social_post/agent.ts";
import { reviewRequest } from "./review_request/agent.ts";
import { seoRecommendations } from "./seo_recommendations/agent.ts";
import { aiVisibilityStub } from "./ai_visibility_stub/agent.ts";
import { invoiceReminder } from "./invoice_reminder/agent.ts";
import { paymentFollowUp } from "./payment_follow_up/agent.ts";
import { weeklyBriefing } from "./weekly_briefing/agent.ts";
import { conversationInsights } from "./conversation_insights/agent.ts";

// v2 department-head skills (new).
import { financialSummary } from "./financial_summary/agent.ts";
import { marketResearch } from "./market_research/agent.ts";
import { pricingMemo } from "./pricing_memo/agent.ts";
import { taxPrep } from "./tax_prep/agent.ts";
import { jobPost } from "./job_post/agent.ts";
import { trainingDoc } from "./training_doc/agent.ts";
import { hrMemo } from "./hr_memo/agent.ts";
import { documentDrafter } from "./document_drafter/agent.ts";

export const sales = defineDepartment({
  agent_id: "sales",
  display_name: "Sales",
  bucket: "sales",
  channel: "sequence",
  purpose: "Brings in new customers and closes business: outreach, follow-ups, quote follow-ups, and quote documents.",
  routes_here_when: [
    "Owner follows up with a lead or prospect",
    "Owner asks to draft a quote or chase an unbooked quote",
    "Owner asks for outreach to win or re-engage customers",
  ],
  strong_signals: ["follow up", "quote", "reach out"],
  // Sales owns quotes and the communication that surrounds them. It does NOT
  // own "a message" generically — that belongs to Customer Service, which is
  // where an inbound reply goes. Claiming the bare `message` subject here made
  // Sales the catch-all for every communication and pulled inbound replies out
  // of Customer Service.
  semantics: {
    subjects: ["quote", "outbound_message"],
    intents: ["communicate", "create"],
  },
  skills: [
    // Generative: makes a NEW quote. Never right for a request about a quote
    // that already exists, which is what `generative` and `servesIntents`
    // together enforce.
    {
      agent: quoteGenerator,
      extraKeywords: ["draft a quote", "write up a quote", "estimate for", "parts", "labor"],
      servesIntents: ["create"],
      generative: true,
    },
    { agent: quoteFollowUp, extraKeywords: ["chase", "hasn't booked", "didn't book"], servesIntents: ["communicate"] },
    { agent: leadNurture, extraKeywords: ["re-engage", "lapsed", "haven't seen", "referral"], servesIntents: ["communicate", "unknown"] },
    { agent: outreach, extraKeywords: ["cold email", "reach out to", "prospect", "outreach", "new business", "cold outreach"], servesIntents: ["communicate"] },
  ],
  defaultSkillId: "lead_nurture",
  // The first department that can send something real. Sales composes exactly
  // as before; when the owner named a recipient address in the ask, the
  // composed text becomes a send_email action the owner approves instead of a
  // draft they copy elsewhere. Anything ambiguous still drafts.
  // See communication_actions.ts.
  // Asked before composing: a communication whose recipient cannot be pinned
  // down has no safe continuation, and drafting to nobody is not one.
  resolveAction: resolveCommunicationAmbiguity,
  resolveActionFromOutput: resolveEmailSendFromOutput,
  // V-02: pipeline-aware skill selection. "Follow up with X on her quote" must
  // pull X's existing quote and run quote-followup, NOT quote-generation (which
  // would ask for line items the owner didn't give). New line items in the ask
  // → quote-generation; a named customer with an open quote + follow-up intent
  // → quote-followup; a named customer with no quote → lead nurture.
  resolveSkill: ({ ownerAsk, params, context }) => {
    const a = ownerAsk.toLowerCase();
    // Explicit new-quote drafting with line items always generates.
    const hasLineItems = /\$\s?\d/.test(ownerAsk) && /(parts|labor|part|materials|each|qty|x\d)/i.test(ownerAsk);
    if (/\b(draft|write up|create|generate|make)\b.*\bquote\b/.test(a) || hasLineItems) return "quote_generator";

    const followUpIntent = /\b(follow up|follow-up|check in|chase|circle back|nudge|touch base)\b/.test(a);
    if (!followUpIntent) return undefined; // keyword scoring handles the rest

    const name = typeof params.customer_name === "string" ? params.customer_name.trim().toLowerCase() : "";
    const lead = name
      ? context.pipelineLeads.find(
          (l) => l.name.toLowerCase().includes(name) && l.quoteAmount && !["won", "lost", "accepted", "cancelled"].includes(l.status.toLowerCase()),
        )
      : undefined;
    if (lead) return "quote_follow_up"; // existing open quote → follow up on it
    // Follow-up intent but no open quote on file → warm nurture, never a fabricated
    // quote. (Covers "follow up with a lead I haven't quoted yet".)
    return "lead_nurture";
  },
  examples: [
    { owner_ask: "Follow up with Sarah Chen on her brake quote.", expected_route: "sales", expected_output_excerpt: "quote" },
    { owner_ask: "Draft a quote for Mike Johnson, parts $620, labor $480, net 15 terms.", expected_route: "sales", expected_output_excerpt: "Total" },
    { owner_ask: "Reach out to the three customers we haven't seen in 6+ months.", expected_route: "sales", expected_output_excerpt: "Hi" },
  ],
});

export const marketing = defineDepartment({
  agent_id: "marketing",
  display_name: "Marketing",
  bucket: "marketing",
  channel: "email",
  purpose: "Advertising, social, email campaigns, content, SEO, reviews, and brand awareness.",
  routes_here_when: [
    "Owner asks for a campaign, social post, blog, or content piece",
    "Owner asks for SEO recommendations or review requests",
  ],
  strong_signals: ["campaign", "post", "blog", "research"],
  // Marketing owns review responses and campaign sends, so it communicates
  // outward as well as creating: a reply to a public review is a marketing
  // task, not a customer-service ticket.
  semantics: {
    subjects: ["campaign", "review"],
    intents: ["create", "analyze", "communicate"],
  },
  skills: [
    { agent: campaign, extraKeywords: ["email blast", "promo", "special", "announce"] },
    { agent: socialPost, extraKeywords: ["facebook", "instagram", "social"] },
    { agent: contentWriter, extraKeywords: ["about us", "blog", "article", "paragraph", "write up"] },
    { agent: reviewRequest, extraKeywords: ["review", "google review", "testimonial"] },
    { agent: seoRecommendations, extraKeywords: ["seo", "search", "rank", "website"] },
    { agent: aiVisibilityStub, extraKeywords: ["ai visibility", "geo score", "chatgpt see"] },
    { agent: marketResearch, extraKeywords: ["what do others charge", "what are competitors", "market check"] },
  ],
  defaultSkillId: "campaign",
  // Sending is a system capability, not a Sales one: any department that writes
  // to a customer can propose the send, under the same authorization and the
  // same approval gate. See communication_actions.ts.
  resolveAction: resolveCommunicationAmbiguity,
  resolveActionFromOutput: resolveEmailSendFromOutput,
  examples: [
    { owner_ask: "Draft an email blast for our June AC special, $59 instead of $89.", expected_route: "marketing", expected_output_excerpt: "59" },
    { owner_ask: "Write a Facebook post about our weekend hours.", expected_route: "marketing", expected_output_excerpt: "weekend" },
    { owner_ask: "Give me SEO recommendations for our website.", expected_route: "marketing", expected_output_excerpt: "SEO" },
  ],
});

export const customerService = defineDepartment({
  agent_id: "customer_service",
  display_name: "Customer Service",
  bucket: "customer_service",
  channel: "widget_reply",
  purpose: "Handles customer questions, complaints, and retention with the hardcoded complaint-safety rules.",
  routes_here_when: [
    "Owner is responding to an inbound customer question",
    "Owner is responding to a complaint or service issue",
  ],
  strong_signals: ["respond to a complaint", "customer asked", "reply to"],
  // Customer Service owns talking to customers when the subject is the
  // conversation itself: an inbound question, a reply, an apology. A message
  // with no other business subject is theirs.
  semantics: {
    subjects: ["complaint", "inbound_message"],
    intents: ["communicate"],
  },
  skills: [
    { agent: complaintHandler, extraKeywords: ["angry", "upset", "complaint", "refund", "unhappy"] },
    { agent: customerQuestion, extraKeywords: ["asked", "question", "do you", "reply", "respond"] },
    { agent: conversationInsights, extraKeywords: ["insights", "what are customers asking", "common questions", "conversation report", "capture rate", "chat trends"] },
  ],
  defaultSkillId: "customer_question",
  // Sending is a system capability, not a Sales one: any department that writes
  // to a customer can propose the send, under the same authorization and the
  // same approval gate. See communication_actions.ts.
  resolveAction: resolveCommunicationAmbiguity,
  resolveActionFromOutput: resolveEmailSendFromOutput,
  examples: [
    { owner_ask: "A customer named Aisha asked: do you handle hybrids? Draft a reply.", expected_route: "customer_service", expected_output_excerpt: "Hi" },
    { owner_ask: "Robert L. is angry his AC recharge didn't hold. Draft a careful response.", expected_route: "customer_service", expected_output_excerpt: "sorry" },
    { owner_ask: "Reply to the customer asking about our weekend hours.", expected_route: "customer_service", expected_output_excerpt: "Hi" },
  ],
});

export const operations = defineDepartment({
  agent_id: "operations",
  display_name: "Operations",
  bucket: "scheduling_ops",
  channel: "sms",
  purpose: "Delivering the service: bookings, reschedules, cancellations, reminders, and day-to-day operational comms.",
  routes_here_when: [
    "Owner is communicating about appointments or scheduling",
    "Owner sends operational updates (closures, delays, order ready)",
  ],
  strong_signals: ["book", "appointment", "reschedule", "reminder"],
  semantics: {
    subjects: ["appointment"],
    intents: ["schedule", "communicate"],
    // Scheduling is Operations' alone: no other department books, reschedules
    // or cancels, so a scheduling ask belongs here whatever else it mentions.
    primaryIntents: ["schedule"],
  },
  skills: [
    { agent: appointmentReminder, extraKeywords: ["reminders", "tomorrow's appointments", "day-before"] },
    { agent: booking, extraKeywords: ["book", "confirm", "reschedule", "cancel", "slot"] },
  ],
  defaultSkillId: "booking",
  // Sending is a system capability, not a Sales one: any department that writes
  // to a customer can propose the send, under the same authorization and the
  // same approval gate. See communication_actions.ts.
  resolveAction: resolveCommunicationAmbiguity,
  resolveActionFromOutput: resolveEmailSendFromOutput,
  examples: [
    { owner_ask: "Mike Johnson called wanting a tire rotation Thursday at 10:30.", expected_route: "operations", expected_output_excerpt: "Thursday" },
    { owner_ask: "Send tomorrow's appointments their day-before reminders.", expected_route: "operations", expected_output_excerpt: "reminder" },
    { owner_ask: "Confirm Maria's Saturday 10am appointment.", expected_route: "operations", expected_output_excerpt: "confirm" },
  ],
});

export const invoicing = defineDepartment({
  agent_id: "invoicing",
  display_name: "Invoicing & Collections",
  bucket: "finance",
  channel: "email",
  purpose: "Sends invoice reminders and follows up on overdue accounts. Always owner-approved; never threatening.",
  routes_here_when: [
    "Owner mentions an outstanding or overdue invoice",
    "Owner wants to send a billing reminder or escalate a past-due notice",
  ],
  strong_signals: ["invoice", "overdue", "past due", "payment"],
  semantics: {
    subjects: ["invoice"],
    intents: ["communicate", "create"],
  },
  skills: [
    { agent: paymentFollowUp, extraKeywords: ["escalate", "past due", "second notice", "final notice", "payment plan"] },
    { agent: invoiceReminder, extraKeywords: ["invoice", "reminder", "outstanding", "unpaid"] },
  ],
  defaultSkillId: "invoice_reminder",
  // Sending is a system capability, not a Sales one: any department that writes
  // to a customer can propose the send, under the same authorization and the
  // same approval gate. See communication_actions.ts.
  resolveAction: resolveCommunicationAmbiguity,
  resolveActionFromOutput: resolveEmailSendFromOutput,
  examples: [
    { owner_ask: "Send Mike Johnson a reminder about his outstanding invoice, $1,100, 8 days overdue.", expected_route: "invoicing", expected_output_excerpt: "invoice" },
    { owner_ask: "Escalate the past-due notice for the Wallace account, this is the second time.", expected_route: "invoicing", expected_output_excerpt: "payment" },
    { owner_ask: "Draft a payment-plan offer for our biggest overdue customer.", expected_route: "invoicing", expected_output_excerpt: "payment" },
  ],
});

export const accounting = defineDepartment({
  agent_id: "accounting",
  display_name: "Accounting & Finance",
  bucket: "finance",
  channel: "report",
  purpose: "Plain-English financial summaries, pricing memos, and tax-prep checklists from the data layer.",
  routes_here_when: [
    "Owner asks for a financial summary or revenue figure",
    "Owner asks for pricing help or a tax-prep reminder",
  ],
  strong_signals: ["revenue", "financial", "pricing", "taxes"],
  semantics: {
    subjects: ["finances"],
    intents: ["analyze", "retrieve", "create"],
  },
  skills: [
    { agent: financialSummary, extraKeywords: ["revenue", "financial", "summary", "receivables", "cash", "income"] },
    { agent: pricingMemo, extraKeywords: ["pricing", "price", "raise", "increase", "charge more"] },
    { agent: taxPrep, extraKeywords: ["tax", "taxes", "quarterly", "941", "irs", "deductions"] },
    // Weekly Briefing remains as a general fallback for broad "how's business" asks.
    { agent: weeklyBriefing },
  ],
  defaultSkillId: "financial_summary",
  examples: [
    { owner_ask: "What was our revenue last week?", expected_route: "accounting", expected_output_excerpt: "Briefing" },
    { owner_ask: "Give me a financial summary for the month.", expected_route: "accounting", expected_output_excerpt: "Briefing" },
    { owner_ask: "Summarize our outstanding receivables.", expected_route: "accounting", expected_output_excerpt: "Briefing" },
  ],
});

export const adminRecords = defineDepartment({
  agent_id: "admin_records",
  display_name: "Customer Data & Administration",
  bucket: "system",
  channel: "report",
  purpose: "Documents, contracts, intake forms, SOPs, and CRM record organization.",
  routes_here_when: [
    "Owner asks for a document, contract, or intake form",
    "Owner asks to update or organize customer records",
  ],
  strong_signals: ["contract", "intake form", "document", "agreement"],
  // The department that owns the customer record itself. `update_record` is a
  // PRIMARY intent because no other department mutates customer data — which is
  // what makes "note on Mike's record that he approved the tire quote" land
  // here rather than in Sales on the strength of the word "quote". Before this
  // declaration the department was unreachable for record work: every routing
  // signal it had came from its document-drafting skills.
  semantics: {
    subjects: ["customer_record", "document"],
    intents: ["update_record", "retrieve", "create", "destroy"],
    primaryIntents: ["update_record"],
  },
  skills: [
    { agent: documentDrafter, extraKeywords: ["contract", "agreement", "intake form", "template", "one-pager", "policy", "sop", "document"] },
    // Content Writer remains as a general fallback for broader copy requests.
    { agent: contentWriter, extraKeywords: ["about us", "blog", "article", "paragraph"] },
  ],
  defaultSkillId: "document_drafter",
  // The first department with a tool path: "add a note to Sarah's record saying
  // she prefers texts" is a thing to DO, so it runs through the action executor
  // (policy -> execution -> verification -> audit) instead of drafting. Anything
  // it does not clearly understand still drafts. See admin_records_actions.ts.
  resolveAction: resolveRecordAction,
  examples: [
    { owner_ask: "Draft a service agreement template for new customers.", expected_route: "admin_records", expected_output_excerpt: "agreement" },
    { owner_ask: "Write up a one-pager on our refund policy.", expected_route: "admin_records", expected_output_excerpt: "refund" },
    { owner_ask: "Generate a new-customer intake form for the front desk.", expected_route: "admin_records", expected_output_excerpt: "intake" },
  ],
});

export const people = defineDepartment({
  agent_id: "people",
  display_name: "People Management",
  bucket: "system",
  channel: "report",
  purpose: "Hiring, training, scheduling, payroll communications, and HR memos.",
  routes_here_when: [
    "Owner is hiring, training, or scheduling employees",
    "Owner needs an HR memo, policy, or payroll communication",
  ],
  strong_signals: ["hire", "job post", "training", "employee", "payroll", "schedule the team"],
  semantics: {
    subjects: ["staff"],
    intents: ["create", "communicate"],
  },
  skills: [
    { agent: jobPost, extraKeywords: ["job post", "craigslist", "hiring ad", "hire", "posting"] },
    { agent: trainingDoc, extraKeywords: ["training", "checklist", "sop", "handbook", "onboarding"] },
    { agent: hrMemo, extraKeywords: ["write up", "write-up", "coaching", "performance", "late", "schedule the team", "mother's day"] },
    // Content Writer remains as a general fallback for broader copy requests.
    { agent: contentWriter, extraKeywords: ["about us", "blog", "article", "paragraph"] },
  ],
  defaultSkillId: "job_post",
  examples: [
    { owner_ask: "Write a Craigslist post for a part-time mechanic, weekends, must have tools.", expected_route: "people", expected_output_excerpt: "mechanic" },
    { owner_ask: "Draft a training checklist for a new front-desk hire.", expected_route: "people", expected_output_excerpt: "training" },
    { owner_ask: "Help me write up an employee who's been late three times this month.", expected_route: "people", expected_output_excerpt: "employee" },
  ],
});

export const DEPARTMENTS = [
  sales,
  marketing,
  customerService,
  operations,
  invoicing,
  accounting,
  adminRecords,
  people,
] as const;
