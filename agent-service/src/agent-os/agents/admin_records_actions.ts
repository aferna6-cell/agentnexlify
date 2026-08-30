/**
 * Customer Data & Administration — the department's tool path.
 *
 * When the owner asks to put a note on a customer's record, the department
 * selects the `add_customer_note` tool and hands it to the action executor; the
 * executor decides whether policy allows it, runs it, verifies it, and records
 * it. The department never touches the tool itself.
 *
 * CRM retrieve tools (get_customer / search_customers) are gated by
 * CRM_ACTIONS_ENABLED (default OFF) so production behaviour matches pre-M8
 * until rollout.
 */

import type {
  ClarificationRequest,
  DepartmentActionRequest,
} from "./_department.ts";
import { authorizesAction, type AskIntent } from "./_intent.ts";
import { describeAmbiguity, resolveCustomerAnywhere } from "./_resolve.ts";
import { crmActionsEnabled } from "../actions/flags.ts";
import type { SharedContext } from "../types/agent.ts";

/** The business's own details, as distinct from a customer's. */
const BUSINESS_PROFILE_RE =
  /\b(my|our|the) (business|company|shop|store)\b|\b(business|company) (name|phone|address|hours|profile|details)\b|\bon file\b/i;

const CUSTOMER_LOOKUP_RE = /\b(customer|lead|client|record|profile|contact)\b/i;

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
 * Decide whether this ask is a CRM / record action.
 *
 * Returns undefined — meaning "not an action, draft instead" — unless the ask
 * clearly names a capability this department owns.
 */
export function resolveRecordAction(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
}): DepartmentActionRequest | ClarificationRequest | undefined {
  const { ownerAsk, params, context, intent } = args;

  if (intent.intent === "retrieve" && BUSINESS_PROFILE_RE.test(ownerAsk)) {
    return {
      toolId: "get_business_profile",
      input: {},
      describe: (result) => {
        const p = result as Record<string, unknown>;
        const parts = Object.entries(p)
          .filter(([, v]) => typeof v === "string" && v)
          .map(
            ([k, v]) =>
              `${k
                .replace(/([A-Z])/g, " $1")
                .toLowerCase()
                .trim()}: ${String(v)}`,
          );
        return parts.length
          ? `Here's what I have on file — ${parts.join(", ")}.`
          : "I don't have a business profile on file yet.";
      },
    };
  }

  if (
    crmActionsEnabled() &&
    intent.intent === "retrieve" &&
    CUSTOMER_LOOKUP_RE.test(ownerAsk)
  ) {
    const customerName =
      typeof params.customer_name === "string"
        ? params.customer_name.trim()
        : "";
    if (!customerName) {
      return { clarify: "Which customer should I look up? Give me a name." };
    }
    const resolution = resolveCustomerAnywhere(context, customerName);
    if (resolution.kind === "multiple") {
      const names = describeAmbiguity(resolution.matches, (m) => m.name);
      return {
        clarify: `I found more than one customer matching "${customerName}" — ${names}. Which one did you mean?`,
      };
    }
    if (resolution.kind === "none") {
      return {
        clarify: `I couldn't find a customer matching "${customerName}" in this business.`,
      };
    }
    if (resolution.match.leadId) {
      return {
        toolId: "get_customer",
        input: { customer_id: resolution.match.leadId },
        describe: (result) => {
          const out = result as { name?: string; status?: string };
          return `Here's ${out.name ?? resolution.match.name} — status ${out.status ?? "unknown"}.`;
        },
      };
    }
    return {
      toolId: "search_customers",
      input: { query: customerName },
    };
  }

  if (intent.intent !== "update_record") return undefined;
  if (!authorizesAction(intent)) return undefined;

  const note = extractNoteText(ownerAsk);
  const customerName =
    typeof params.customer_name === "string" ? params.customer_name.trim() : "";

  if (!customerName) {
    return {
      clarify:
        "I can add that note — which customer's record should it go on? " +
        "Tell me the name and I'll queue it up.",
    };
  }

  const resolution = resolveCustomerAnywhere(context, customerName);

  if (resolution.kind === "multiple") {
    const names = describeAmbiguity(resolution.matches, (m) => m.name);
    return {
      clarify: `I found more than one customer matching "${customerName}" — ${names}. Which one did you mean?`,
    };
  }

  if (resolution.kind === "none") return undefined;

  if (!note) {
    return {
      clarify: `What should the note on ${resolution.match.name}'s record say?`,
    };
  }

  return {
    toolId: "add_customer_note",
    input: { customer_name: resolution.match.name, note },
    describe: (result) => {
      const out = result as {
        customerName?: string;
        note?: string;
        durable?: boolean;
      };
      const where =
        out.durable === false
          ? " (this environment stores notes in memory only)"
          : "";
      return `Added a note to ${out.customerName ?? resolution.match.name}'s record: "${out.note ?? note}"${where}.`;
    },
  };
}
