# Feature: Per-Tenant Intent Configuration

**Status:** Draft
**Author:** AI analysis (2026-04-24)
**Date:** 2026-04-24
**Motivation:** `knowledge-base/wiki/ai-llm/intent-engineering-tenant-ai-alignment.md`
**Ship bar:** Widget agent for any tenant with `intent_config` set optimizes for that tenant's declared primary goal, not the platform default.

---

## 1. Problem Statement

AgentNexLiFy widget agents currently apply the same optimization function to every tenant. A plumbing company and a law firm get the same "capture lead, be helpful" objective. This is the Klarna failure pattern replicated at scale: the agent does exactly what the system prompt says, but not what the tenant's business actually needs.

Current state:
- `widget_configs.custom_instructions` (TEXT) — free-form prose injected into the system prompt. Tenant-specific, but not machine-readable or structured.
- No declared primary goal per tenant.
- Constraints are buried in KB prose or `custom_instructions` text, invisible to the platform.
- No trade-off hierarchy (speed vs accuracy vs safety).
- No escalation triggers defined structurally — only KB-level guidance.
- No audit trail linking agent decisions to declared intent at time of conversation.

Result: when a widget agent handles a conversation poorly, the debugging path is: read conversation → guess what the system prompt was → guess what KB content was retrieved. No ground truth.

This spec defines `intent_config`: a per-tenant JSONB configuration that makes intent explicit, versionable, and injected as structured context into every widget system prompt.

---

## 2. Goals / Non-Goals

### Goals

- Add `intent_config` JSONB column to `widget_configs` table.
- Define a canonical JSON schema for `intent_config` with documented fields.
- Inject `intent_config` into widget system prompts as structured context, above `custom_instructions`.
- Expose `intent_config` in the dashboard widget settings page (read + write).
- Log active `intent_config` version on each conversation start for audit trail.
- Provide default `intent_config` values per vertical (plumbing, medical, legal, retail) as presets.
- Keep backward compatibility: tenants without `intent_config` get existing behavior unchanged.

### Non-Goals (V1)

- Per-conversation dynamic intent (intent is set at tenant level, not per-session).
- A/B testing of intent configs (V2).
- Intent scoring or analytics dashboard (V2 — track which intents correlate to booked appointments).
- Automatic intent inference from KB content (V2).
- Real-time intent config hot-reload mid-conversation (V2 — restart conversation on config change).
- Nested/conditional intents ("if customer is returning, use intent B").
- Multi-goal weighting (V1 supports a single primary goal with secondary fallback).

---

## 3. Intent Config Schema

```json
{
  "schema_version": "1.0",
  "primary_goal": "book_appointment",
  "secondary_goal": "capture_lead",
  "success_metric_label": "Appointment booked or contact info captured",
  "tone": "professional_warm",
  "trade_off_hierarchy": ["accuracy", "safety", "speed"],
  "constraints": [
    "never_promise_pricing_without_qualification",
    "always_ask_for_service_address_before_pricing",
    "skip_qualification_if_customer_mentions_emergency"
  ],
  "escalation_triggers": [
    "customer_expresses_frustration_after_3_messages",
    "question_outside_knowledge_base_scope",
    "explicit_legal_or_medical_question",
    "customer_requests_human"
  ],
  "preset": "trades"
}
```

### Field definitions

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | yes | Schema version for migration compatibility. Start at `"1.0"`. |
| `primary_goal` | enum | yes | What the agent optimizes for. See enum values below. |
| `secondary_goal` | enum | no | Fallback if primary is not achievable (e.g. can't book → capture lead). |
| `success_metric_label` | string | no | Human-readable description of what success looks like. For dashboard display. |
| `tone` | enum | yes | Communication style injected into system prompt. |
| `trade_off_hierarchy` | string[] | no | Ordered priority list when goals conflict. Values: `accuracy`, `safety`, `speed`, `thoroughness`, `brevity`. |
| `constraints` | string[] | no | Hard rules the agent must follow. Mapped to prose in system prompt injection. |
| `escalation_triggers` | string[] | no | Conditions that trigger "I'll connect you with a team member." |
| `preset` | string | no | Named preset template used as base. For display and audit purposes. |

### `primary_goal` enum values

| Value | Description |
|---|---|
| `book_appointment` | Primary win is a booked appointment in the calendar |
| `capture_lead` | Primary win is name + contact info captured |
| `qualify_lead` | Primary win is a scored/qualified lead (budget, timeline, fit) |
| `answer_question` | Primary win is customer question resolved accurately |
| `generate_quote` | Primary win is a quote or estimate delivered |
| `general_support` | Mixed support; no dominant conversion goal |

### `tone` enum values

| Value | Description |
|---|---|
| `professional_warm` | Business-appropriate but personable |
| `casual_friendly` | Relaxed and conversational |
| `formal` | Structured, conservative |
| `urgent_direct` | Fast, direct — for emergency services |

---

## 4. User Stories

### Tenant (business owner)

1. As a plumber, I want my widget to prioritize booking appointments over collecting email addresses, so the agent doesn't waste time asking for newsletter opt-ins when a customer needs service today.
2. As a law firm, I want the agent constrained from giving specific legal advice, so I'm not exposed to liability from AI-generated legal opinions.
3. As a medical practice, I want accuracy prioritized over speed, so the agent never gives a fast but wrong answer about symptoms or medication.
4. As an e-commerce store, I want the agent to answer product questions accurately before trying to capture a lead, because a wrong product answer kills the sale.

### Developer

5. As a backend developer, I want `intent_config` injected before `custom_instructions` in the system prompt so it sets the frame before tenant-specific overrides.
6. As a backend developer, I want a `NULL` `intent_config` to produce identical behavior to the current system (backward compatible, no regression).
7. As a backend developer, I want the active `intent_config` logged to `conversations` at conversation start so debugging has a ground truth.

### Platform operator

8. As an operator debugging a conversation, I want to see which `intent_config` version was active when the conversation started, so I can understand what the agent was optimizing for.
9. As an operator, I want vertical presets (trades, medical, legal, retail) so onboarding a new tenant defaults to a sensible intent configuration for their industry.

---

## 5. Schema Changes

### Migration: `112_intent_config.sql`

```sql
-- 112: Add intent_config JSONB to widget_configs for per-tenant agent intent
ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS intent_config JSONB DEFAULT NULL;

COMMENT ON COLUMN widget_configs.intent_config IS
  'Per-tenant AI intent configuration. Declares primary_goal, tone, constraints, '
  'escalation_triggers, and trade_off_hierarchy. Injected as structured context '
  'into widget system prompts before custom_instructions. NULL = platform default behavior.';

-- Log intent_config version on conversation start for audit trail
ALTER TABLE conversations
  ADD COLUMN IF NOT EXISTS intent_config_snapshot JSONB DEFAULT NULL;

COMMENT ON COLUMN conversations.intent_config_snapshot IS
  'Snapshot of widget_configs.intent_config at conversation start. '
  'Audit trail: allows debugging which intent was active for a given conversation.';
```

---

## 6. API Contract

### GET `/api/widget-config` (existing endpoint)
Add `intent_config` field to response.

### PATCH `/api/widget-config` (existing endpoint)
Accept `intent_config` in request body. Validate against schema before saving.

### GET `/api/widget-config/intent-presets` (new)
Returns the built-in preset library: `trades`, `medical`, `legal`, `retail`, `ecommerce`, `general`.

```json
{
  "presets": {
    "trades": {
      "primary_goal": "book_appointment",
      "tone": "professional_warm",
      "trade_off_hierarchy": ["speed", "accuracy"],
      "constraints": ["never_promise_pricing_without_qualification"],
      "escalation_triggers": ["customer_expresses_frustration_after_3_messages"]
    },
    "medical": {
      "primary_goal": "answer_question",
      "tone": "formal",
      "trade_off_hierarchy": ["accuracy", "safety", "speed"],
      "constraints": ["always_recommend_consulting_a_doctor", "never_diagnose"],
      "escalation_triggers": ["medical_emergency_keywords", "patient_in_distress"]
    },
    "legal": {
      "primary_goal": "capture_lead",
      "tone": "formal",
      "trade_off_hierarchy": ["accuracy", "safety"],
      "constraints": ["never_provide_specific_legal_advice", "always_recommend_consultation"],
      "escalation_triggers": ["explicit_legal_question", "urgent_legal_matter"]
    }
  }
}
```

---

## 7. System Prompt Injection

In `backend/services/widget_chat_helpers.py`, the system prompt builder should inject `intent_config` as structured context. Example injection block:

```
<intent_config>
Your primary goal for this conversation: BOOK AN APPOINTMENT.
If you cannot book an appointment, your secondary goal is: CAPTURE LEAD (name + contact info).

Communication tone: professional and warm — friendly but business-appropriate.

Priority when goals conflict: accuracy first, then safety, then speed.

Hard constraints (must follow at all times):
- Never promise pricing without first asking for the service address and type of work.
- Skip qualification steps if the customer mentions an emergency.

Escalate to a human team member when:
- The customer expresses frustration after 3 messages.
- The question is outside the scope of the knowledge base.
- The customer explicitly requests a human.
</intent_config>
```

Placement: after tenant identity/KB context, before `custom_instructions`. `custom_instructions` can override intent_config prose if they conflict — tenant wins on explicit overrides.

---

## 8. Implementation Order

1. Migration `112_intent_config.sql` — adds columns, backward-safe (both nullable).
2. `backend/services/widget_chat_helpers.py` — intent injection into system prompt builder.
3. `backend/routers/widget_config.py` — add `intent_config` to GET/PATCH + new presets endpoint.
4. `backend/schemas/widget_config.py` — add `IntentConfig` Pydantic model with validation.
5. Dashboard page update — widget settings form, preset selector, field editor.
6. `conversations` snapshot — log `intent_config_snapshot` on conversation creation in `backend/services/widget_chat.py`.

---

## 9. Acceptance Criteria

- [ ] Tenant with `intent_config = NULL` gets identical widget behavior to current (no regression).
- [ ] Tenant with `intent_config.primary_goal = "book_appointment"` gets system prompt that prioritizes booking over other outcomes.
- [ ] `conversations.intent_config_snapshot` is populated on every new conversation start.
- [ ] PATCH `/api/widget-config` with invalid `intent_config` shape returns 422.
- [ ] GET `/api/widget-config/intent-presets` returns all six presets.
- [ ] Dashboard widget settings page shows preset selector and current `intent_config`.
- [ ] Unit test: `build_system_prompt()` with `intent_config` set includes `<intent_config>` block.
- [ ] Unit test: `build_system_prompt()` with `intent_config = None` matches current output exactly.

---

## 10. Open Questions

1. Should `intent_config` be editable by the tenant themselves (self-serve) or ops-gated (only admin can set)? V1 recommendation: ops-gated, surfaced in widget settings but explained in onboarding.
2. Should preset selection happen at onboarding wizard time or only in widget settings? Recommendation: onboarding wizard step — "What is the primary thing your widget should do for customers?"
3. Do we need per-vertical constraint catalogs (a menu of constraint options) or free-form string entry? V1: free-form in UI, validated against an allowlist on the backend to prevent injection.
4. How do we handle `escalation_triggers` that need NLU (e.g. "customer expresses frustration") vs literal keyword triggers? V1: map known trigger IDs to prose in the prompt; future work is semantic trigger detection.

---

## Related

- `knowledge-base/wiki/ai-llm/intent-engineering-tenant-ai-alignment.md` — motivation and framing
- `migrations/072_widget_custom_instructions.sql` — existing `custom_instructions` pattern this builds on
- `backend/services/widget_chat_helpers.py` — system prompt injection point
- `backend/services/support_agent.py` — current system prompt assembly (reads `knowledge_base` + `custom_instructions`)
- `specs/onboarding-v2_spec.md` — onboarding wizard where preset selection could live
