# Agent OS Overhaul — Grill-Me Interview Notes (WIP)

Status: **interview in progress** — 5 of 7 branches resolved. Not a spec yet.
Branch: `claude/agent-os-grill-resume-cHznV` (continued from
`claude/nexlify-os-overhaul-51nga`, commit 26aac47). Started 2026-05-21.
Next: Branch 6 (Onboarding/Memory) questions posed to user, awaiting answers →
finish 7 → hand to `write-prd` → `specs/agent-os-overhaul_spec.md`.
No code until that spec is approved.

This file is the durable record of the design interview (the
`.claude/agent-comms/checkpoint.md` copy is gitignored and does not survive the
ephemeral cloud container).

---

## Concept

Turn AgentNexLiFy into a chat-first "Agent OS". User signs up, gives a website
link + onboarding answers → builds AI memory/context. User chats with an
orchestrator chatbot that interprets each prompt and delegates to a best-fit
specialist agent. Agents request connectors (e.g. Gmail) from the user as needed.
No-fit requests go to a backlog for review and later implementation. The existing
embeddable chat widget stays — becomes a feature of the OS, and the AI can pull
customer data from it.

---

## Resolved decisions

### Branch 1 — Vision & North Star
- OS is **just the chatbot**; dashboard mostly disappears (survivors in Branch 4).
- Users: small-business **owner + staff/team**. End customers only touch the embedded widget.
- Embedded widget becomes a **feature of** the OS. Existing customers **migrated over** (not a separate SKU).
- Hero use case: **build a marketing campaign**. User wants "all of these" by launch — flagged as scope creep, force-rank in Branch 7.
- Orchestrator's job = delegate user task to the correct specialist agent.
- Success = people **actually paying for and using** the product.
- No competitor anchor named. Comparables to research: GoHighLevel AI Employee, Lindy, Replit Agent.

### Branch 2 — Orchestrator & Routing
- Routing = **LLM classifier**. User imagined Opus 4.7 orchestrator → Sonnet agents; **worried about API cost**. Advisor note: Haiku routes, Opus only for real reasoning, Sonnet does agent work (existing advisor-executor pattern).
- User can **see all agent runs + thought process** as a flowchart; wrong-agent picks → user reports a bug → fix.
- Orchestrator **can spin up multiple agents** for multi-step requests.
- Agents run **async**; post back to chat when finished (Claude/ChatGPT-style).
- **Separate conversations** per task, but orchestrator **retains memory** across all conversations + overall business details.
- Orchestrator is **always the entry point** (no direct-to-agent access).
- **Approval gates required**: agents draft emails / recommend purchases / draft posts — **final decision always the user's**. No risky autonomous actions.

### Branch 3 — Agent Model & No-Fit Backlog
- Agent definitions, exact roster, agent boundaries = **delegated to Claude's discretion**. Preference: **fewer agents**, keep it simple.
- User **selects business type**; agent roster **changes based on business type**.
- **No force-fit**: no agent fits → orchestrator says "we don't have that capability."
- Backlog flow: no-fit request → **email to owner (Aidan)** → if approved → to-do list / backlog.
- New agent ships → **user (and anyone who gains access) notified** to try it.
- **Distinguish no-agent vs agent-failed**: never say an agent doesn't exist when it does — communicate the specific agent failed → bug sent to Aidan to review/fix.
- No-fit requests **logged for later**; owner has no bandwidth to handle each live.

### Branch 4 — Dashboard / Data Display
- "Show my leads" → agent renders a **table inside chat**, AND a standalone **Leads page** exists for viewing anytime without the chatbot.
- Pipeline / analytics / inbox **survive as real pages**; agent can deep-reference them in chat.
- **Settings page survives.**
- Conversations **inbox survives as a page**; agent can also surface conversations in chat.
- Agent deliverables (drafts) **reviewed in chat** — user open to a better surface if advised (recommendation: side panel / doc editor beats chat bubbles for editing drafts).
- **Launch surface = chat + survivors: Leads page, Conversations inbox, Settings.** Everything else rolls into agent functionality.
- **Desktop-first.** iOS app much later.

### Branch 5 — Connectors / OAuth / Tools
- **Connector request UX**: agent prompts the user **in chat** for any connector it
  needs ("Connect X" in-conversation) — no upfront setup gate.
- **Launch connector set**: all existing connectors (Google Calendar, Facebook,
  Google Business Profile, Zapier) **plus Gmail, "social media", and "Microsoft
  Office"**. "Social media" and "Microsoft Office" are umbrella terms — exact
  platforms/scopes unresolved → force-rank in Branch 7.
- **Email sending**: through the user's **connected Gmail** (OAuth, sends "from
  them") — **user must approve every send first** (matches Branch 2 approval gate).
- **Connector catalog**: **one flat catalog** (not business-type-scoped). Agent
  invokes a connector only when the user's request requires it.
- **Token security** (user deferred to Claude's discretion — recommendation):
  **app-level encryption-at-rest** for OAuth refresh/access tokens in
  `tenant_integrations` (envelope encryption, key from env/secret manager).
  Reuse the existing `tenant_integrations` table — **no dedicated vault for v1**.
- **Missing connector mid-task**: agent **pauses, asks for the connector, then
  continues** once connected (approval-gate pattern — not fail, not partial).
- **Connector failure (revoked/expired)**: **Settings banner** shows what is
  connected; user can **manually connect any connector** from Settings anytime.

---

## Remaining branches to grill

- **Branch 6 — Onboarding & Memory/Context**: website-link ingestion (reuse onboarding crawl → KB), other onboarding questions, orchestrator cross-conversation memory storage/retrieval, per-tenant memory schema, staleness.
- **Branch 7 — Scope / MVP / Cost / Success / Failure modes**: force-rank the hero workflow, define the day-1 MVP cut, pin the LLM cost model, define a concrete success metric, enumerate failure-mode fallbacks.

---

## Existing infrastructure to reuse (codebase map)

This overhaul is mostly a **re-conception of the interaction model + an orchestrator
layer** on top of substantial existing infra — NOT a from-scratch build.

- 79 backend routers in `backend/routers/` (auth, onboarding, widget_chat, leads, conversations, automations, marketing_campaigns, integrations, billing, etc.).
- Runtime agent infra exists: `backend/services/managed_agents_registry.py` (~10 Anthropic Managed Agents — lead_qualifier, document_drafter, support_agent, deep_researcher, data_analyst, appointment_booker, etc.), `advisor_executor.py` (Opus advisor → Sonnet/Haiku executor), `managed_agents.py`, `llm_runtime.py`, `support_agent.py` (widget fallback).
- Widget chat endpoint: `POST /api/v1/widget/chat` in `backend/routers/widget_chat.py` (Sonnet-first, Opus fallback via FALLBACK_TO_SUPPORT_AGENT token).
- Onboarding: `POST /api/v1/onboarding/{tenant_id}/complete` already crawls a website URL → Claude → structured KB, auto-seeds FAQs. `tenants` table has business_name, industry, plan, onboarding_completed_at, autopilot_enabled.
- KB: stored in `widget_configs.knowledge_base`; embeddings via Voyage AI (voyage-3-lite, 512d) + pgvector.
- OAuth connectors exist: Google Calendar (`integrations.py`), Facebook (`channels_facebook.py`), Google Business Profile (`gbp.py`), Zapier (`zapier.py`).
- 77 frontend pages in `frontend/src/pages/`.

## Branch 5 — Connectors / OAuth / Tools (RESOLVED 2026-05-21)

Codebase grounding: `tenant_integrations` table (migration 109) stores OAuth
tokens; `backend/routers/integrations.py` has working Google OAuth with
signed-JWT state; Facebook / Google Business Profile / Zapier connectors exist.

Raw Q&A (user answers verbatim, lightly normalized):
1. Connector request UX → agent prompts user in chat for any connector it needs.
2. Launch connector set → all existing connectors + Gmail + social media + Microsoft Office.
3. Email sending → through the user's connected Gmail, but user must approve each send first.
4. Connector catalog → one flat catalog; agent only invokes a connector the request requires.
5. Token security bar → user deferred ("up to your discretion").
6. Missing connector mid-task → pause, request the connector, then continue afterwards.
7. Connector failure → Settings banner of connection status + manual connect from Settings.

Resolved decisions folded into the "Branch 5" entry under Resolved decisions above.

## Branch 6 — Onboarding & Memory/Context (questions posed 2026-05-21, AWAITING ANSWERS)

Codebase grounding: `POST /api/v1/onboarding/{tenant_id}/complete` already
crawls a website URL → Claude → structured KB and auto-seeds FAQs. KB lives in
`widget_configs.knowledge_base`; embeddings via Voyage AI (voyage-3-lite, 512d)
+ pgvector. `tenants` table has business_name, industry, plan,
onboarding_completed_at, autopilot_enabled.

7 questions sent to user:
1. Onboarding shape — wizard form vs a conversation with the orchestrator itself; beyond website link + business type, what minimum facts collected (goals, brand voice, team, target customer)?
2. Website ingestion — homepage-only vs full-site crawl; behavior when business has no website; one-time at signup vs scheduled re-crawl.
3. Memory contents — business facts only vs also decisions/preferences/past agent outputs; who can edit or delete memory (owner only vs any staff).
4. Memory write trigger — orchestrator auto-decides what to remember vs explicit "remember this" vs both.
5. Memory retrieval — load full memory every orchestrator turn vs semantic retrieval of relevant slices (reuse Voyage AI + pgvector).
6. Staleness — how memory stays current: manual Settings edits vs periodic re-crawl vs agent flags contradictions when it notices them.
7. Memory vs widget KB — orchestrator memory same store as `widget_configs.knowledge_base` vs separate; does widget customer data feed orchestrator memory.

## Open tensions (not yet settled)
- "All hero workflows by day 1" is scope creep — force-rank to one MVP workflow (Branch 7).
- "Social media" and "Microsoft Office" connectors (Branch 5 Q2) are umbrella terms — pin exact platforms/scopes and force-rank in Branch 7.
- LLM orchestration cost model not yet pinned.
- Draft-editing surface (chat vs side panel) — recommend side panel; user open to it.

## Schema invariants (CLAUDE.md — must hold in any implementation)
`client_id` not `tenant_id` on leads/conversations; `status` not `lead_stage`;
`areas_of_interest` not `service_interest`; widget JS byte-identical between `widget/`
and `frontend/public/widget/`; no `from __future__ import annotations` in FastAPI files;
schema changes only via numbered `migrations/NNN_*.sql`.
