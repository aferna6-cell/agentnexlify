# AgentNexLiFy — Agent OS Rehaul: Partner Brief

**Date:** 2026-05-25
**Author:** Aidan
**Status:** Group A in flight (7 of 8 phases shipped); Groups B & C planned
**Branch:** `claude/agent-os-grill-resume-cHznV` → draft PR #177

---

## 1. What we're building (one paragraph)

AgentNexLiFy is a multi-tenant SaaS where every small-business customer gets an
embeddable chat widget that captures leads, books appointments, and runs
follow-ups. The "Agent OS" is the layer underneath the widget that lets one
orchestrator read **every** customer message a tenant gets — not just widget
chat — and act on it (draft replies, book meetings, mark unsubscribes, escalate
to the owner). The rehaul is split into three groups. **Group A (inbound)**
gets every customer message INTO the OS. **Group B (actions)** lets the OS act
back OUT. **Group C (sync)** keeps the OS view consistent with the rest of the
app.

---

## 2. Why it matters (business framing)

| Question partners ask | Answer |
|---|---|
| Why not just use the chat widget? | Widget covers ~30% of customer touchpoints. Email + SMS + Facebook DMs are the other 70%. Without ingesting those, the OS is blind to most leads. |
| What does this unlock commercially? | Tier-up path. Today: $99/mo (widget only). After rehaul: $250/mo Pro = "all your customer channels in one inbox + AI that drafts replies." Same surface GoHighLevel charges $497/mo for. |
| Who's the competition? | GoHighLevel ($97-497/mo, AI Employee tier), Drillbit (YC, contractor-focused), Birdeye/Podium ($300-600/mo). Our positioning: widget-first onboarding + vertical knowledge-base per tenant (not generic GPT replies). |
| What's the moat? | Tenant-isolated knowledge base — every tenant trains the AI with their own service catalog, pricing, FAQs. Generic LLM competitors can't ground answers in a salon's specific pricing. |
| Tenant lock-in? | Multi-channel ingest. Once a tenant routes their email + SMS + FB through us, ripping us out means rebuilding 4 webhook integrations. |

---

## 3. The three groups (full scope)

### Group A — Inbound Connectors (THIS SPRINT, in flight)

Every customer message from widget / email / SMS / Facebook lands in `os_threads`
+ `os_messages` so the orchestrator can read it.

8 phases. **7 complete and pushed to the draft PR. 1 verification phase pending.**

### Group B — Action Connectors (NEXT SPRINT)

Orchestrator acts on what it reads:
- Outbound SMS replies (Twilio)
- Outbound email replies (Resend / Postmark)
- Calendar bookings (Google + Microsoft)
- Approval-gated send (owner clicks "send" or "auto-send" toggle per tenant)

### Group C — Sync (FOLLOW-UP)

Keeps OS inbox consistent with existing surfaces:
- OS thread reads from widget → mirror to `conversations` / `chat_messages` so
  existing dashboard pages don't lose data
- OS thread sends to SMS → mirror to Twilio thread history
- OS thread reads email → mirror to Gmail/Postmark archive

---

## 4. Group A — What's DONE (with proof)

7 commits on `claude/agent-os-grill-resume-cHznV`. All tests written. All
passing locally where dependencies installed.

| Phase | What shipped | Commit |
|---|---|---|
| **1. Foundation** | Migration `124_os_threads_inbound.sql` — adds `source`, `source_thread_id`, `source_metadata`, `inbound_kind`, `source_ref` columns + unique dedup index. Bridge service skeleton `os_inbound_bridge.py` with 4 async functions (one per source). Toggle config helpers. | `c92e9b0a` |
| **2. Widget bridge** | Widget POST handler now fires `bridge_widget` as fire-and-forget background task. Widget response time unchanged (never blocks on bridge). | `953b61f3` |
| **3. Settings API** | Owner-only `POST /api/v1/os/inbound/bridge-toggle` + `GET /api/v1/os/inbound/bridge-config` endpoints. Pydantic-validated source field. | `57600878` |
| **4. Email bridge** | `POST /api/v1/os/inbound/email/{provider}` with HMAC sig verify for Postmark + Mailgun. Auto-reply detection (Auto-Submitted / Precedence headers). Cross-tenant lookup by inbound email address. 8 tests. | `3453afd6` |
| **5. SMS bridge** | `POST /api/v1/os/inbound/sms` with Twilio HMAC-SHA1 sig verify. STOP keyword detection → flips `leads.unsubscribed=true`. Tenant resolved by `To` number. Returns valid TwiML. 6 tests. | `11609ec6` |
| **6. Facebook bridge** | Plug-in to existing Facebook webhook (`channels_facebook.py`). Fires `bridge_facebook` after `ingest_channel_message` returns. Fail-open — bridge exceptions never break the FB 5s retry budget. 5 tests. | `a1d2eafb` |
| **7. Settings UI** | New page `frontend/src/pages/SettingsInboundChannels.jsx`. 4 toggles (Widget / Email / SMS / Facebook). Dark theme matches dashboard. Optimistic UI with error retry. Sidebar nav entry + lazy-loaded route. `npm run build` clean. | `62cd97d4` |

### Engineering invariants enforced

- All bridges fail-open. If a bridge crashes, the inbound webhook still
  returns 200. Customer never sees an outage caused by the OS layer.
- All bridges idempotent. `source_ref` field stores `<source>:<message_id>`;
  provider retries don't double-insert.
- Tenant isolation. Bridges resolve `client_id` via existing provider →
  tenant lookup tables. No defaulting to "first tenant".
- HMAC signature verification on every external webhook. 401 on
  Postmark/Mailgun mismatch; 403 on Twilio mismatch (matches Twilio's own
  convention).
- No new background workers. All bridges run on FastAPI `BackgroundTasks`,
  same process. No new infra cost.

---

## 5. Group A — What's TODO

### Phase 8 — Self-verification (small, ~30 min)

Final gate before merging the PR:

1. Run full pytest suite on `os_inbound_*` tests (deps installed mid-session;
   re-run to confirm green).
2. Run `test_os_mvp_e2e.py` regression — make sure existing OS chat shell
   still works.
3. Manual smoke: send a widget message in dev, confirm row appears in
   `os_threads` with `source='widget'`.
4. Flip widget toggle off in the new Settings UI, confirm next message does
   NOT create an `os_thread`.
5. Add verification line to PR description.
6. Mark PR #177 ready-for-review.
7. Merge to `main`.

### Housekeeping (parallel with Phase 8)

- File GitHub issue for 21 pre-existing CI test failures (unrelated to this
  work — but should be triaged before merge so we don't ship into a red
  baseline).
- Update `plans/agent-os-next-steps_plan.md` checkboxes.
- Tag PR with `agent-os` + `connectors-inbound` labels.

---

## 6. Group B — Action Connectors (NEXT, not started)

Orchestrator reads inbound. Now it needs to act.

### Scope

| Action | Provider | Approval model |
|---|---|---|
| Send SMS reply | Twilio (existing account) | Owner approves OR per-tenant auto-send toggle |
| Send email reply | Resend (primary) + Postmark (inbound provider, also outbound-capable) | Same |
| Book calendar slot | Google Calendar (existing OAuth) + Microsoft 365 (new OAuth) | Auto-send when slot is open + customer confirmed |
| Update CRM lead | Internal (`leads` table) | Auto |
| Escalate to owner | Internal (notification system) | Auto |

### Build order (rough)

1. Outbound SMS via existing Twilio client + approval gate
2. Outbound email via existing Resend client + approval gate
3. Calendar booking (Google first, MS later)
4. Per-tenant auto-send toggle in Settings UI
5. Tests + verification

**Estimate:** ~5-7 working days. Mostly wiring existing clients to new
orchestrator action handlers.

---

## 7. Group C — Sync (FOLLOW-UP, not started)

The OS inbox and the existing dashboard surfaces (Conversations page, widget
history) need to stay consistent so the owner sees the same thread no matter
which page they're on.

### Scope

- Bi-directional mirror: OS reply → write to `chat_messages` (widget),
  Twilio thread (SMS), email archive (email). And vice versa.
- Conflict resolution: if owner sends from Conversations page directly,
  reflect into OS thread.
- Read-state sync: marking a message read in one surface marks it read in
  both.

**Estimate:** ~3-5 working days. Mostly trigger functions + background jobs.

---

## 8. Open architectural decision (need partner alignment)

**Question: who builds the orchestrator agent runtime?**

Two options:

| Option | What | Cost | Lock-in |
|---|---|---|---|
| A. DIY runtime | Extend our existing `advisor_executor.py` pattern (Opus advises, Sonnet executes). Build the agent loop ourselves on top of the Anthropic API. | ~$0.30-0.75 per orchestrator turn (Sonnet-heavy). Owns 100% of the agent logic. | None. Can swap models per-tenant. |
| B. Claude Managed Agents | Use Anthropic's hosted Managed Agents service. Less code to write. | Premium pricing tier (~2-3x DIY). | Anthropic platform lock. |

**Current recommendation: DIY (Option A).** Reasons:
1. We already have `advisor_executor.py` working in production for
   `advised_lead_qualifier` + `advised_document_drafter`.
2. Unit economics — at $99-250/mo per tenant, the ~3x cost premium of
   Managed Agents eats too much margin.
3. We need per-tenant model swap (some tenants will want Haiku for cost,
   some Opus for quality). DIY makes that trivial.
4. We can ship Group B on top of DIY runtime immediately. Managed Agents
   means rewriting the existing pattern first.

Partner ask: agree on DIY before Group B starts. ETA on this decision: this
week.

---

## 9. Risks + mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Email signature spoofing | Low | HMAC verified per provider; reject 401 on mismatch. Tested. |
| Twilio STOP-loop (STOP triggers reply triggers STOP) | Low | Existing `leads.unsubscribed` flag respected by orchestrator + rule engine. Verified before shipping Phase 5. |
| Customer sends 1000 msgs in a burst → Sonnet bill spike | Medium | Existing `usage_meter` per-tenant cap. Bridge still records the inbound message but orchestrator refuses to route. |
| Migration 124 conflicts with concurrent main-branch work | Low | Branch isolated; number re-verified at apply time. |
| 21 pre-existing CI failures hide a new regression | Medium | Triage + file issue before merge. Don't ship into a red baseline. |
| Group A merges but Group B slips → orchestrator reads but can't act | High | Acceptable. Group A is independently valuable (owner sees unified inbox). Group B can ship 2-3 weeks later without rework. |

---

## 10. What partners are being asked

1. **Sign off on DIY runtime** (Option A in §8). Required before Group B
   starts.
2. **Email provider call.** Postmark vs Mailgun for inbound. Both ship in
   the bridge code already — pick one for the default tenant config based on
   billing preference.
3. **Calendar OAuth app registrations.** Google + Microsoft 365 dev apps need
   to be created under our org account before Group B can ship.
4. **Pricing tier decision.** Does multi-channel inbound move from $99/mo
   into the $250/mo Pro tier, or does it ship at $99/mo to drive widget
   conversions? Recommend Pro tier for margin.

---

## 11. Timeline (rough)

| Milestone | Target | Status |
|---|---|---|
| Group A code complete | Today (2026-05-25) | DONE (Phases 1-7) |
| Group A verification + merge | This week | TODO (Phase 8) |
| Partner alignment on Option A + email provider | This week | OPEN |
| Group B start | Next week | BLOCKED on partner sign-off |
| Group B ship | +2 weeks from start | NOT STARTED |
| Group C ship | +1 week after Group B | NOT STARTED |
| All three groups in prod | ~4 weeks from today | PROJECTED |

---

## 12. Where to look

- **Live draft PR:** GitHub PR #177 on `aferna6-cell/agentnexlify`
- **Source plan:** `plans/agent-os-connectors-inbound_plan.md`
- **Source spec:** `specs/agent-os-connectors-inbound_spec.md`
- **Action connectors spec (Group B):** `specs/agent-os-connectors-actions_spec.md`
- **Sync spec (Group C):** `specs/agent-os-connectors-sync_spec.md`
- **Bridge code:** `backend/services/os_inbound_bridge.py`
- **Settings UI:** `frontend/src/pages/SettingsInboundChannels.jsx`

---

## Quick read for non-engineers

We made the platform stop being deaf. Today the AI only hears chat-widget
messages. After this work it hears widget + email + SMS + Facebook. That's
the difference between "automated FAQ bot" ($99/mo ceiling) and "AI front
desk" ($250+/mo) — same code we wrote, different product.

7 of 8 phases shipped this week. 1 verification phase left. Then we move to
making the AI **respond** through those same channels (Group B), and finally
keep the views in sync across the dashboard (Group C). Four weeks to all
three groups in production.
