/**
 * Customer Data & Administration — the department's tool path.
 *
 * When the owner asks to put a note on a customer's record, the department
 * selects the `add_customer_note` tool and hands it to the action executor; the
 * executor decides whether policy allows it, runs it, verifies it, and records
 * it. The department never touches the tool itself.
 *
 * CRM retrieve + mutation tools (get_customer / search_customers /
 * create_customer / update_customer / update_lead_stage) are gated by
 * CRM_ACTIONS_ENABLED (default OFF) so production behaviour matches pre-M8
 * until rollout. Notes stay ungated Level-1.
 */

import type {
  ClarificationRequest,
  DepartmentActionRequest,
} from "./_department.ts";
import { authorizesAction, type AskIntent } from "./_intent.ts";
import { extractParams } from "./_extract.ts";
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

/** Stage-move phrasing: "move X to contacted", "mark X as won", pipeline stage. */
const STAGE_ASK_RE = /\b(pipeline\s+stage|lead\s+stage|status|stage)\b/i;
const STAGE_MOVE_RE = /\b(?:move|mark)\s+.+\s+(?:to|as)\s+['"]?[a-z]/i;

/** Field-update phrasing without requiring the word "record". */
const FIELD_ASK_RE =
  /\b(update|change|set)\b[\s\S]{0,80}\b(phone|email|address|name)\b/i;

function isStageAsk(ask: string): boolean {
  if (STAGE_MOVE_RE.test(ask)) return true;
  if (STAGE_ASK_RE.test(ask) && /\b(to|as|into)\b/i.test(ask)) return true;
  return false;
}

function isFieldAsk(ask: string): boolean {
  return FIELD_ASK_RE.test(ask);
}

function isNoteAsk(ask: string): boolean {
  return /\b(note|notes|noting)\b/i.test(ask);
}

function customerNameFrom(params: Record<string, unknown>): string {
  return typeof params.customer_name === "string"
    ? params.customer_name.trim()
    : "";
}

/** Only explicitly supplied create fields — never invent missing ones. */
function explicitCreateFields(
  params: Record<string, unknown>,
): Record<string, unknown> {
  const input: Record<string, unknown> = {};
  const name = customerNameFrom(params);
  if (name) input.name = name;
  if (typeof params.email === "string" && params.email.trim()) {
    input.email = params.email.trim().toLowerCase();
  }
  if (typeof params.phone === "string" && params.phone.trim()) {
    input.phone = params.phone.trim();
  }
  if (typeof params.address === "string" && params.address.trim()) {
    input.address = params.address.trim();
  }
  if (typeof params.status === "string" && params.status.trim()) {
    input.status = params.status.trim().toLowerCase().replace(/\s+/g, "_");
  }
  return input;
}

/** Only fields the ask clearly targets AND supplies a value for. */
function explicitUpdateFields(
  params: Record<string, unknown>,
  ask: string,
): Record<string, string> {
  const fields: Record<string, string> = {};
  if (
    /\bphone\b/i.test(ask) &&
    typeof params.phone === "string" &&
    params.phone.trim()
  ) {
    fields.phone = params.phone.trim();
  }
  if (
    /\bemail\b/i.test(ask) &&
    typeof params.email === "string" &&
    params.email.trim()
  ) {
    fields.email = params.email.trim().toLowerCase();
  }
  if (
    /\baddress\b/i.test(ask) &&
    typeof params.address === "string" &&
    params.address.trim()
  ) {
    fields.address = params.address.trim();
  }
  return fields;
}

function blank(v: unknown): boolean {
  return (
    v === undefined || v === null || (typeof v === "string" && v.trim() === "")
  );
}

/** Prefer orchestrator params; fill gaps from the ask so Haiku omissions cannot drop explicit CRM fields. */
function crmParams(
  ownerAsk: string,
  params: Record<string, unknown>,
): Record<string, unknown> {
  const extracted = extractParams(ownerAsk);
  const merged: Record<string, unknown> = { ...extracted, ...params };
  for (const key of [
    "customer_name",
    "email",
    "phone",
    "address",
    "status",
  ] as const) {
    if (blank(params[key]) && !blank(extracted[key])) {
      merged[key] = extracted[key];
    }
  }
  return merged;
}

export function resolveRecordAction(args: {
  ownerAsk: string;
  params: Record<string, unknown>;
  context: SharedContext;
  intent: AskIntent;
}): DepartmentActionRequest | ClarificationRequest | undefined {
  const { ownerAsk, params: rawParams, context, intent } = args;
  const params = crmParams(ownerAsk, rawParams);

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

  // --- Create customer / lead (CRM flag required) --------------------------
  if (intent.intent === "create") {
    if (!authorizesAction(intent)) return undefined;
    if (!crmActionsEnabled()) return undefined;
    // Only CRM creates — leave quote/invoice/document creates to their departments.
    if (
      intent.subjectType !== "customer_record" &&
      !/\b(lead|customer|client|contact)\b/i.test(ownerAsk)
    ) {
      return undefined;
    }

    const input = explicitCreateFields(params);
    if (typeof input.name !== "string" || !input.name) {
      return {
        clarify:
          "I can create that lead — what name should I use? " +
          "I'll only save fields you explicitly give me.",
      };
    }

    return {
      toolId: "create_customer",
      input,
      describe: (result) => {
        const out = result as {
          name?: string;
          email?: string;
          phone?: string;
          status?: string;
          deduplicated?: boolean;
        };
        const bits = [
          out.name ?? String(input.name),
          out.email,
          out.phone,
          out.status ? `status ${out.status}` : undefined,
        ].filter(Boolean);
        return out.deduplicated
          ? `Found an existing customer matching those details — ${bits.join(", ")}.`
          : `Created customer ${bits.join(", ")}.`;
      },
    };
  }

  // --- Update record: stage / fields / note --------------------------------
  if (intent.intent !== "update_record") return undefined;
  if (!authorizesAction(intent)) return undefined;

  const stageAsk = isStageAsk(ownerAsk);
  const fieldAsk = isFieldAsk(ownerAsk);
  const noteAsk = isNoteAsk(ownerAsk) && !stageAsk && !fieldAsk;

  // Stage move (CRM flag required). Invalid stages are rejected by the tool.
  if (stageAsk) {
    if (!crmActionsEnabled()) return undefined;
    const customerName = customerNameFrom(params);
    if (!customerName) {
      return {
        clarify:
          "I can update the pipeline stage — which customer did you mean?",
      };
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
    if (!resolution.match.leadId) {
      return {
        clarify: `I found ${resolution.match.name}, but I don't have a customer id for them in this business's CRM.`,
      };
    }
    const status =
      typeof params.status === "string" && params.status.trim()
        ? params.status.trim().toLowerCase().replace(/\s+/g, "_")
        : "";
    if (!status) {
      return {
        clarify: `What pipeline stage should I move ${resolution.match.name} to?`,
      };
    }
    return {
      toolId: "update_lead_stage",
      input: { customer_id: resolution.match.leadId, status },
      describe: (result) => {
        const out = result as {
          name?: string;
          previousStatus?: string;
          status?: string;
        };
        return `Moved ${out.name ?? resolution.match.name} from ${out.previousStatus ?? "unknown"} to ${out.status ?? status}.`;
      },
    };
  }

  // Field update (CRM flag required). Only explicitly supplied fields change.
  if (fieldAsk) {
    if (!crmActionsEnabled()) return undefined;
    const customerName = customerNameFrom(params);
    if (!customerName) {
      return {
        clarify: "I can update that record — which customer did you mean?",
      };
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
    if (!resolution.match.leadId) {
      return {
        clarify: `I found ${resolution.match.name}, but I don't have a customer id for them in this business's CRM.`,
      };
    }
    const fields = explicitUpdateFields(params, ownerAsk);
    if (Object.keys(fields).length === 0) {
      return {
        clarify: `What should I change on ${resolution.match.name}'s record? Tell me the new phone, email, or address.`,
      };
    }
    return {
      toolId: "update_customer",
      input: { customer_id: resolution.match.leadId, fields },
      describe: (result) => {
        const out = result as {
          name?: string;
          updatedFields?: string[];
        };
        const changed = (out.updatedFields ?? Object.keys(fields)).join(", ");
        return `Updated ${out.name ?? resolution.match.name} (${changed}).`;
      },
    };
  }

  // Notes remain ungated Level-1 (existing behaviour).
  if (!noteAsk && !/\b(note|notes|noting|log|jot)\b/i.test(ownerAsk)) {
    // An update_record ask we don't understand → draft, don't guess a mutation.
    return undefined;
  }

  const note = extractNoteText(ownerAsk);
  const customerName = customerNameFrom(params);

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
