# Nexlify Capabilities Roadmap — Assistant Surface Expansion

**Date:** 2026-08-01
**Status:** DRAFT — needs owner review, then per-capability specs via write-prd
**Source:** owner idea dump (continuous inbox monitoring, SMS replies, social drafting + image gen, X timeline, lead scraping, in-chat connector requests, downloadable personal-assistant app) mapped against a full two-repo capability survey.

This is a sequencing plan, not a spec. Each phase below turns into its own `specs/<feature>_spec.md` before build (write-prd → grill-me → prd-to-issues per `.claude/rules/daily-skills.md`). <!-- drift-skip -->

---

## Where we stand (survey summary, 2026-08-01)

| Idea | Exists today | Gap |
|---|---|---|
| Inbox monitoring | Webhook inbound email only (Postmark/Mailgun → `backend/routers/os_inbound.py` → `os_inbound_bridge`). Outbound via Resend (`email_sender.py`) + M365 Graph (`m365_mail.py`). `support_agent.py` answers with confidence + `escalate_reason` — widget only. | No Gmail, no IMAP, no polling. No triage loop. No first-class escalation object. |
| Text replies | Full Twilio stack: `twilio_webhooks.py` (missed-call textback, inbound reply), `sms.py` (outbound), BYO subaccounts, compliance/opt-outs, `backend/services/os_actions/sms.py`. | No multi-turn SMS conversation agent. Inbound SMS bridge is opt-in and defaults off. No MMS. |
| Social drafts + images | `social_media.py` (AI post/campaign gen, calendar), Instagram publish via Graph API (`backend/services/os_actions/social_instagram.py`), FB + GBP handlers, `image_gen.py` (OpenAI gpt-image-1 only), `content_repurpose.py` (x_thread format). | Image gen not wired into post flow. No scheduled-publish worker for `social_posts.scheduled_for`. No engagement ingestion. |
| X timeline | `twitter` is a platform enum + prompt limits in `social_media_ai.py`. | Zero X API integration — no OAuth, no posting client, no timeline read. |
| Lead scraping | `prospects/scrape_prospects.py` + `populate_prospects.py` — offline scripts writing xlsx. `outreach/` is docs only. `website_crawler.py` exists but scoped to tenant's own site. | Nothing productized. No `prospects` table, no tenant scoping, no enrichment, no compliance guardrails. |
| In-chat connector requests | `connector_awareness.py` — regex inference in OS chat, posts connect-path link once per connector per thread. | Link-only (no in-chat OAuth, no return-to-thread). Registry is a hardcoded dict covering ~5 connectors. Three inconsistent storage tables (`integrations`/`tenant_integrations`/`tenant_api_keys`, `tenant_id` vs `client_id`). |
| Downloadable app | Nothing. `specs/agent-os-overhaul_spec.md` lines 42 + 344 make mobile an explicit non-goal. Agent-Nexlify-OS repo is merged demo/spec only — no native code. | Everything. Requires reversing a documented non-goal. |

Full inventory with file paths captured in the survey that produced this plan; key handoff path today: widget `HANDOFF_REQUESTED` marker → `widget_chat_effects.py:99` → `"handoff"` tag in `conversations.tags` → owner SMS/email/webhook → team reply via `conversation_inbox.py`.

---

## Phase 1 — Escalation substrate + connector unification (foundation)

Everything the owner asked for funnels through two shared pieces. Build these first or every later phase hand-rolls its own version.

### 1a. First-class escalations
- New `escalations` table (migration): `client_id`, source (`widget|email|sms|os`), thread ref, reason, priority, status, `assigned_to`, SLA timestamps. Replaces the `"handoff"` magic string as source of truth (tag stays for widget back-compat during transition — no half migration; one PR moves all call sites).
- Escalation create path callable from any surface, not just widget. `support_agent.py` `escalate_reason` output wires into it.
- Surface in the existing conversation inbox (`conversation_inbox.py` + `ConversationsPage.jsx`) with status/priority. Notification legs reuse existing SMS/email; add push later.
- Return-to-bot flow (today the handoff tag is never removed by any code path).

### 1b. Unified connector registry + in-chat connect
- DB-driven connector registry replacing the hardcoded dict in `connector_awareness.py`: provider, label, scopes, connect path, status. Reconcile the three storage tables behind one read API (do NOT rename columns yet — read-side unification only; schema consolidation is its own later migration).
- Deep-link OAuth: `state` JWT (pattern already exists in `integrations.py`) carries the OS thread id → callback redirects back into the thread → assistant posts "connected, resuming."
- Chat UI: inline connect card instead of a bare path link.
- This is the exact mechanic the owner described: "if it becomes clear agent nexlify needs access to a tool it should request that connection straight in chat."

**Deliverable:** escalation object live in inbox; connector request → connect → resume loop working for Google Calendar (already-built OAuth) as the proof case.

---

## Phase 2 — Continuous support-inbox monitoring

The flagship ask. Builds directly on Phase 1.

- **Gmail connector** (biggest gap — most small businesses live in Gmail): OAuth (read + send scopes) stored via the Phase 1 registry + existing `integration_key_vault.py` encryption. Poll via Gmail `history.list` from the existing 5-min tier of `main._automation_loop`; upgrade to Pub/Sub `watch` push later if latency matters. IMAP as a fallback connector for non-Gmail mailboxes (separate, later).
- **Normalize into the existing bridge:** polled messages feed `bridge_email` exactly like Postmark/Mailgun webhooks — idempotency already anchored on `os_messages.source_ref`. No parallel pipeline.
- **Triage loop** (new service): Haiku classifies each inbound (spam / info-only / answerable / escalate). Answerable → draft grounded reply via the `support_agent.py` pattern with tenant KB. Confidence below threshold or sensitive topic → escalation (Phase 1a) + notify.
- **Send policy:** drafts-only by default (matches the platform's Drafts-Only Approval Loop principle and existing `os_auto_send_rules`). Tenant opts into auto-send per category with confidence threshold. Approve-from-inbox already exists (`os_email_actions.py` signed HMAC links) — reuse it so the owner can approve replies from their phone without logging in.
- Plan gate: `agent_os` tier.

**Deliverable:** tenant connects Gmail in chat, agent watches the inbox continuously, answers what it can (drafts or auto-send), escalates the rest with notification.

---

## Phase 3 — SMS conversation agent

- Multi-turn SMS runtime reusing the widget chat pipeline (KB grounding, extraction, booking) keyed on phone number ↔ lead. Inbound path already exists (`/api/v1/os/inbound/sms` + `bridge_sms`); what's missing is the conversational loop and lead/session mapping.
- Escalation + triage shared with Phase 2 (same classifier, same escalation object).
- Compliance already solid: STOP handling, opt-outs (`160_sms_opt_outs.sql`), rate limiter, TCPA guardrails in `sms_compliance.py` — extend, don't rebuild.
- Flip `sms_enabled` default discussion: keep opt-in, but make it a one-toggle in onboarding.

---

## Phase 4 — Social: images wired in, scheduled publish, X integration

### 4a. Close existing gaps (cheap, high value)
- Wire `image_gen.py` into the social post composer: generate → preview → attach to Instagram container publish (two-step Graph flow already implemented). Add per-platform size presets. Consider adding an Anthropic/Gemini image provider to the existing provider abstraction. <!-- drift-skip -->
- Scheduled-publish worker: automation-loop job that scans `social_posts.scheduled_for` and dispatches through the existing `os_actions/social_*` handlers. Table + status enum already support it.
- Engagement ingestion into the existing `engagement_data` jsonb (IG/FB Graph insights first).

### 4b. X/Twitter (new integration)
- OAuth 2.0 PKCE connector via Phase 1 registry; post tweets (`os_actions/social_twitter.py` mirroring the Instagram handler) <!-- drift-skip -->; read the connected account's timeline + mentions.
- Timeline read feeds a digest into Agent OS ("what's happening in your feed / who mentioned you") and grounds post drafting.
- **DECISION NEEDED (owner):** X API pricing — free tier is write-only-ish and rate-crippled; Basic is ~$200/mo per app. This is a real recurring cost and may need its own plan gate or usage-based pass-through. Do not build until priced.

---

## Phase 5 — Lead prospecting engine

Productize what `prospects/` does offline, with compliance built in.

- `prospects` table (migration, `client_id`-scoped) + backend service: discover → enrich → verify → score → promote to `leads` with `source='prospecting'`.
- **Prefer APIs over scraping:** Google Places API for local-business discovery (the actual use case the offline scripts approximate) instead of SERP/Yelp scraping — ToS-safe and more reliable. Keep `website_crawler.py` (Cloudflare Browser Rendering) for enriching a discovered prospect's site.
- Email verification before any outreach (ZeroBounce-class API).
- Outbound cold email stays third-party per `outreach/email-infra-setup.md` ("never send cold mail from agentnexlify.com") — export to Instantly/Smartlead via the existing Zapier surface first; native compliant sequences are a later decision.
- **DECISION NEEDED (owner):** scraping posture (API-only vs mixed), and whether cold outreach ever runs through the platform (CAN-SPAM/TCPA exposure lands on us if it does).

---

## Phase 6 — Downloadable personal-assistant app (horizon)

- **Conflicts with a documented non-goal** (`specs/agent-os-overhaul_spec.md`: desktop-first, mobile "much later"). Proceeding requires an ADR in `planning/decisions/` reversing it — owner call, not build-team call.
- Staged path that avoids a premature native build:
  1. **PWA first** — installable on phone + desktop from the existing dashboard, push notifications (also gives Phase 1 escalations a push leg). 90% of "downloadable app" perception for ~5% of the cost.
  2. **Wrap later** — Capacitor (mobile) / Tauri (desktop) around the same frontend if app-store presence starts mattering commercially.
  3. Native only if a capability demands it (background inbox sync doesn't — the server does the monitoring; the app is a viewport + notification surface).
- "Easier setup than OpenClaw" is already the architecture: hosted multi-tenant backend, setup = sign in + connect accounts through the Phase 1 in-chat connector flow. No self-hosting, no config files.

---

## Sequencing rationale

```
Phase 1 (escalations + connectors)
   ├──> Phase 2 (inbox)      — needs Gmail connector + escalation object
   ├──> Phase 3 (SMS agent)  — needs escalation object; infra otherwise ready
   ├──> Phase 4 (social/X)   — 4a independent; 4b needs connector registry
   └──> Phase 5 (prospecting)— independent, but sells better once 2–4 exist
Phase 6 (app) — after 1–3 prove the assistant loop; PWA can start anytime
```

Phases 2 and 3 are the same product story ("the agent watches your channels and only interrupts you when it must") — ship them close together.

## Open decisions for owner

1. X API tier + cost pass-through (Phase 4b blocker).
2. Scraping posture: API-only or mixed (Phase 5 blocker).
3. Cold outreach in-platform vs export-only (Phase 5).
4. Reverse the mobile non-goal via ADR, and PWA-first vs straight-to-wrapper (Phase 6).
5. Auto-send defaults for inbox replies: drafts-only forever, or opt-in auto-send with thresholds (Phase 2 — recommend drafts-only default, per-category opt-in).

## Next steps

1. Owner reviews this plan; answers open decisions (or defers the blocked phases).
2. Phase 1 → `specs/escalations_spec.md` + `specs/connector-registry_spec.md` via write-prd, then grill-me, then prd-to-issues. <!-- drift-skip -->
3. Phase 2 → `specs/inbox-monitoring_spec.md` once Phase 1 issues are cut. <!-- drift-skip -->
