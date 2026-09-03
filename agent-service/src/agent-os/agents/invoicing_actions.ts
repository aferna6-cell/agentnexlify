/**
 * Invoicing & Collections — action resolver (no drafts → no send_email).
 *
 * PR2 wiring goal: owner asks should become Action Executor tool requests:
 *   - Bill Steve $850 for termite treatment, due in 14 days
 *       → create_invoice_draft (L1 internal write, no owner approval)
 *   - Send that invoice to Steve / approve & send
 *       → send_invoice (L2 owner-approval; data plane only)
 *   - Overdue reminder / escalate past due
 *       → send_invoice_reminder (L2 owner-approval; data plane only)
 *   - Explicit reminder on paid / non-overdue
 *       → no action + clarification (never substitute send_invoice)
 *
 * Hard rule: never invent/mis-target a customer or invoice. If the ask
 * matches 0 or >1 candidates, return a clarification request.
 */

import type {
  DepartmentActionRequest,
  ClarificationRequest,
} from "./_department.ts";
import type { AskIntent } from "./_intent.ts";
import { resolveCustomerAnywhere } from "./_resolve.ts";
import type { SharedContext, InvoiceData } from "../types/agent.ts";

type InvoiceToolIntent = "create" | "send" | "reminder";

function normalize(s: string): string {
  return s.trim().toLowerCase().replace(/\s+/g, " ");
}

function methodFromAsk(ask: string): "email" | "sms" | "both" {
  const a = ask.toLowerCase();
  const wantsSms = /\b(text|sms|txt|message)\b/i.test(ask);
  const wantsEmail = /\bemail|inbox/i.test(ask);
  if (wantsSms && wantsEmail) return "both";
  if (wantsSms) return "sms";
  return "email";
}

function invoiceNumberTokenFromAsk(ask: string): string | undefined {
  // Prefer explicit invoice identifiers like:
  //   invoice #INV-ABCD-001
  //   inv INV-ABCD-001
  //   invoice #1042
  const m = ask.match(/\b(?:invoice|inv)\s*#?\s*([A-Za-z0-9-]{2,})\b/i);
  if (!m) return undefined;
  const token = m[1]!.trim();
  const cleaned = token.startsWith("#") ? token.slice(1) : token;
  // Never treat generic words (e.g. "to") as invoice numbers.
  // Invoice numbers in this system always include digits.
  return /\d/.test(cleaned) ? cleaned : undefined;
}

function customerNameFromAskFallback(ask: string): string | undefined {
  const patterns: RegExp[] = [
    // "Bill Steve $850 ..."
    /\bbill\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\b/i,
    // "Send the invoice to Steve"
    /\b(?:send|email|text)\s+(?:the\s+)?invoice\s+to\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\b/i,
    // "Remind Steve about ..."
    /\bremind\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\b/i,
    // "Reminder to Steve ..."
    /\breminder\s+to\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\b/i,
  ];

  const matches: string[] = [];
  for (const re of patterns) {
    const m = ask.match(re);
    if (m?.[1]) matches.push(m[1]!.trim());
  }

  // Never guess: only accept when we have exactly one unique candidate.
  const uniq = [...new Set(matches.map(normalize))];
  if (uniq.length !== 1) return undefined;
  return matches.find((m) => normalize(m) === uniq[0]);
}

function dueInDaysFromAsk(ask: string): number | undefined {
  const m = ask.match(/\bdue\s+(?:in\s+)?(\d{1,3})\s+days?\b/i);
  if (!m) return undefined;
  const n = Number(m[1]);
  return Number.isFinite(n) && n > 0 ? Math.min(365, Math.floor(n)) : undefined;
}

function dueDateISOFromAsk(ask: string): string | undefined {
  const m = ask.match(/\bdue\s+(?:on\s+)?(\d{4}-\d{2}-\d{2})\b/i);
  if (!m) return undefined;
  return m[1]!.trim();
}

function itemsFromAsk(
  ask: string,
  amount: number,
): { description: string; quantity: number; unit_price: number }[] | undefined {
  // Minimal safe extraction for PR2:
  // "Bill Steve $850 for termite treatment, due in 14 days"
  // Take the first "for <thing>" segment before "due".
  const m = ask.match(/\bfor\s+(.+?)(?=\s*,?\s*(?:due|on)\b|$)/i);
  const desc = m?.[1]?.trim();
  if (!desc) return undefined;
  const cleaned = desc.replace(/^["“']|["”']$/g, "").trim();
  if (!cleaned) return undefined;
  // One-line invoice: unit_price == total when quantity defaults to 1.
  return [
    {
      description: cleaned.length > 500 ? cleaned.slice(0, 500) : cleaned,
      quantity: 1,
      unit_price: amount,
    },
  ];
}

function matchInvoices(args: {
  context: SharedContext;
  customerName?: string;
  invoiceNumberToken?: string;
  amount?: number;
}): InvoiceData[] {
  const { context, customerName, invoiceNumberToken, amount } = args;
  const invoices = context.invoices ?? [];
  let out = invoices;

  if (customerName) {
    const cn = normalize(customerName);
    out = out.filter((i) => normalize(i.customerName) === cn);
  }

  if (invoiceNumberToken) {
    const token = invoiceNumberToken.trim();
    const digitsOnly = /^\d+$/.test(token);
    out = out.filter((i) => {
      if (!i.number) return false;
      if (!digitsOnly) return i.number === token;
      // Digits-only token matches the numeric suffix of the stored number.
      return (
        i.number === token ||
        i.number.endsWith(`-${token}`) ||
        i.number.endsWith(token)
      );
    });
  }

  if (typeof amount === "number" && Number.isFinite(amount)) {
    const want = Math.round(amount * 100) / 100;
    out = out.filter((i) => Math.round(i.amount * 100) / 100 === want);
  }

  return out;
}

function resolveInvoiceToolIntent(
  ownerAsk: string,
  params: Record<string, unknown>,
  intent: AskIntent,
): InvoiceToolIntent | undefined {
  // Draft markers explicitly request words, not actions.
  if (intent.authorization === "draft_only") return undefined;

  const a = ownerAsk.toLowerCase();

  // Reminder/escalation.
  if (
    /\boverdue\b/i.test(ownerAsk) ||
    /\b(past due|past-due)\b/i.test(ownerAsk) ||
    /\b(reminder|unpaid)\b/i.test(ownerAsk) ||
    /\bescalat|final notice|collections\b/i.test(ownerAsk)
  ) {
    return "reminder";
  }

  // Default send path: "send the invoice", "approve and send", "send it".
  if (/\b(send|approve)\b/i.test(ownerAsk)) return "send";

  // Billing / creating a draft invoice.
  const amount = typeof params.amount === "number" ? params.amount : undefined;
  if (amount !== undefined) {
    // Tight so "Send invoice to Steve" doesn't get treated as a create.
    if (/\b(bill|charge)\b/i.test(ownerAsk)) return "create";
    if (/\b(draft|create|prepare)\b[\s\S]{0,50}\binvoice\b/i.test(ownerAsk))
      return "create";
  }

  return undefined;
}

export function resolveInvoicingAction(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
}): DepartmentActionRequest | ClarificationRequest | undefined {
  const { ownerAsk, params, context, intent } = args;

  // Only handle invoice subject asks.
  if (intent.subjectType !== "invoice") return undefined;

  const toolIntent = resolveInvoiceToolIntent(ownerAsk, params, intent);
  if (!toolIntent) return undefined;

  const customerNameFromParams =
    typeof params.customer_name === "string"
      ? params.customer_name.trim()
      : undefined;
  const customerName =
    customerNameFromParams ?? customerNameFromAskFallback(ownerAsk) ?? "";
  const invoiceNumberToken = invoiceNumberTokenFromAsk(ownerAsk);
  const amount =
    typeof params.amount === "number" && Number.isFinite(params.amount)
      ? params.amount
      : undefined;

  const method = methodFromAsk(ownerAsk);

  // --- create_invoice_draft -------------------------------------------------
  if (toolIntent === "create") {
    if (!customerName) {
      return { clarify: "Who should I bill? Tell me the customer's name." };
    }
    if (typeof amount !== "number" || !Number.isFinite(amount) || amount <= 0) {
      return {
        clarify:
          "What amount should I bill? Add the dollar amount (e.g. $850).",
      };
    }

    const resolution = resolveCustomerAnywhere(context, customerName);
    if (resolution.kind === "none") {
      return {
        clarify: `I couldn't find a customer matching "${customerName}" in this business.`,
      };
    }
    if (resolution.kind === "multiple") {
      // We do not have a safe disambiguator beyond a direct question.
      return {
        clarify: `I found multiple customers matching "${customerName}". Which one should I bill?`,
      };
    }

    if (!resolution.match.leadId) {
      return {
        clarify: `I can’t create an invoice for "${customerName}" because I don’t have a customer record id for them.`,
      };
    }

    const items = itemsFromAsk(ownerAsk, amount);
    if (!items) {
      return {
        clarify:
          "What service/line item should I invoice? Include a short phrase like “for termite treatment” so I can itemize it.",
      };
    }

    const dueInDays = dueInDaysFromAsk(ownerAsk);
    const dueDate = dueDateISOFromAsk(ownerAsk);

    return {
      toolId: "create_invoice_draft",
      input: {
        customer_id: resolution.match.leadId,
        items,
        tax_rate: 0,
        ...(dueDate ? { due_date: dueDate } : {}),
        ...(dueInDays ? { due_in_days: dueInDays } : {}),
      },
      describePending: () =>
        "I created the draft invoice. Approve sending when you're ready.",
      describe: () => "Draft invoice created.",
    };
  }

  // --- send_invoice / send_invoice_reminder --------------------------------
  const invoiceMatches = matchInvoices({
    context,
    customerName: customerName || undefined,
    invoiceNumberToken,
    amount,
  });

  if (invoiceMatches.length === 0) {
    if (invoiceNumberToken && customerName) {
      return {
        clarify: `I couldn't find an invoice for ${customerName} matching "${invoiceNumberToken}".`,
      };
    }
    if (customerName)
      return {
        clarify: `I couldn't find an invoice for ${customerName} in this business.`,
      };
    return {
      clarify:
        "Which invoice should I send? Include the invoice number or the customer name.",
    };
  }

  if (invoiceMatches.length > 1) {
    return {
      clarify:
        "I found more than one matching invoice. Tell me the invoice number (e.g. INV-… or #1042) so I can pick the right one.",
    };
  }

  const invoice = invoiceMatches[0]!;

  // Reminder tool must only be proposed for overdue invoices. An explicit
  // reminder ask on paid or non-overdue is no action + explanation — never
  // a substituted send_invoice (that would change the owner's requested act).
  if (toolIntent === "reminder") {
    if (invoice.status !== "overdue") {
      if (invoice.status === "paid") {
        return {
          clarify: `Invoice ${invoice.number} is already paid, so I didn't queue a reminder or a resend. Tell me if you meant a different invoice.`,
        };
      }
      return {
        clarify: `Invoice ${invoice.number} isn't overdue, so I didn't queue a reminder. Ask me to send the invoice if that's what you wanted instead.`,
      };
    }

    return {
      toolId: "send_invoice_reminder",
      input: { invoice_id: invoice.id, method },
      describePending: () =>
        `I queued an overdue invoice reminder to ${invoice.customerName} (Invoice ${invoice.number}). Approve to send.`,
      describe: (result) => {
        const out = result as {
          emailSent?: boolean;
          smsSent?: boolean;
          deduplicated?: boolean;
          invoiceNumber?: string;
        };
        if (out?.deduplicated)
          return `Reminder already sent for invoice ${invoice.number}.`;
        return `Overdue reminder queued and sent for invoice ${invoice.number}.`;
      },
    };
  }

  // toolIntent === "send"
  return {
    toolId: "send_invoice",
    input: { invoice_id: invoice.id, method },
    describePending: () =>
      `I queued invoice send to ${invoice.customerName} (Invoice ${invoice.number}). Approve to send.`,
    describe: () => `Sent invoice ${invoice.number}.`,
  };
}
