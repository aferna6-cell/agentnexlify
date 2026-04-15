---
name: ubiquitous-language
description: Extract a DDD-style domain glossary from conversation, code, or specs. Surface AgentNexLiFy term mismatches (client_id vs tenant_id, status vs lead_stage). Output to docs/glossary.md. Load when user says "glossary", "ubiquitous language", "domain terms", "what does X mean here".
origin: https://github.com/mattpocock/skills/tree/main/ubiquitous-language
version: 1.0.0
triggers:
  - ubiquitous language
  - extract glossary
  - domain terms
  - what does X mean here
  - clarify naming
  - DDD glossary
---

# Ubiquitous Language — Domain Glossary

Force same words for same things across code, docs, conversations, and tenant-facing UI. Prevents the `client_id` vs `tenant_id` class of bug.

## When to Use
- New feature spec that introduces vague terms
- Onboarding a new contributor (human or LLM)
- Refactor where naming inconsistency hides bugs
- Pre-PRD step alongside `grill-me`
- Dispute over what to call something

## When NOT to Use
- Single-file change with no new concepts
- Trivial naming (variable scope only)
- User explicitly named the term

## Process
1. **Source extraction** — pull terms from conversation + code + specs + UI
2. **Cluster** — group synonyms (e.g., "tenant", "client", "business", "customer org")
3. **Pick canonical** — one word per concept, justify
4. **Audit codebase** — grep for synonyms, list locations using non-canonical
5. **Output** to `docs/glossary.md` (create if missing)
6. **Flag mismatches** — anywhere code/UI/docs use a non-canonical term

## AgentNexLiFy canonical terms (load this in every glossary)

| Concept | Canonical | NEVER use | Why |
|---|---|---|---|
| Tenant org | `client_id` (column) / "tenant" (prose) | `tenant_id` on leads/conversations | Schema decision; 3+ prod bugs from mismatch |
| Lead status | `status` | `lead_stage` | `lead_stage` column never existed |
| Areas tagged | `areas_of_interest` | `service_interest` | `service_interest` column never existed |
| End-user using widget | "lead" or "visitor" | "user" | "user" reserved for tenant operators |
| Tenant operator | "user" or "operator" | "client" (overloaded) | "client" overloaded with tenant org |
| Subscription tier | "plan" | "tier", "level" | Stripe-aligned |
| Plan names | `free`, `growth`, `professional`, `autopilot`, `enterprise` | `foundation`, `operations` | Retired; never use |
| Chat instance | "conversation" | "session", "thread" | DB table is `conversations` |
| Single message | "message" | "msg", "entry" | DB table is `messages` |
| Booked slot | "appointment" | "booking" (in code) | DB table is `appointments` |
| Knowledge content | "knowledge base" / "KB" | "wiki" | wiki = LLM-compiled secondary surface |
| Compiled wiki | "wiki" | "KB" | wiki is the LLM-edited Karpathy pattern |
| Widget script | "widget" | "chatbot script", "embed" | Widget is the embeddable JS file |
| Tenant-facing site | "dashboard" | "admin", "console" | URL is /dashboard |

## Glossary template (`docs/glossary.md`)
```markdown
# AgentNexLiFy Domain Glossary

> Single source of truth for naming. Disagreements: edit this file, link the PR.

## Core Entities
- **Tenant** — business that pays for AgentNexLiFy. Schema: `tenants` table. Foreign key: `client_id`.
- **Lead** — visitor captured by the widget. Schema: `leads.client_id`.
- **Conversation** — chat session in the widget. Schema: `conversations.client_id`.
...

## Reserved Terms (DO NOT redefine)
- `client_id` — tenant FK on leads/conversations. Never `tenant_id`.
- `status` — lead status. Never `lead_stage`.
- `areas_of_interest` — JSON array of tagged interests. Never `service_interest`.

## Plan Names (current)
- free, growth ($249), professional ($499), autopilot ($299), enterprise ($899)
- LEGACY: growth $199, professional $399, enterprise $799 (billed on old contracts)
- RETIRED: foundation, operations (NEVER use)

## Audit Findings (this session)
| Term used | Canonical | Locations | Action |
|---|---|---|---|
| <e.g. tenant_id> | client_id | backend/routers/x.py:42 | Fix in PR |
```

## Cross-refs
- `CLAUDE.md` — Critical Invariants section (rules 1-3)
- `.claude/skills/schema-guard/SKILL.md` — enforces canonical names in queries/migrations
- `.claude/rules/schema-discipline.md` — schema rule details
- `.claude/skills/grill-me/SKILL.md` — pair to surface terms early in spec process
