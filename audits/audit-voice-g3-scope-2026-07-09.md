# Audit — G3 Voice/Phone Live-Answering Scope — 2026-07-09

Verdict up front: a real (not stub) live-AI answering loop exists and is tested, but it is a
3-round batch `<Gather>` loop with no booking, no per-tenant number provisioning, no minutes
metering, no calls dashboard UI, and one frontend bug that blocks current `agent_os` customers
from even enabling it.

## 1. What exists today

- **Inbound webhook + tenant routing** — `backend/routers/calls.py:221-321` `/api/v1/calls/voice/incoming`,
  Twilio signature verified (`verify_twilio_request`, calls.py:223). Tenant matched by
  `_find_tenant_by_phone` (calls.py:138-167): scans up to **50 tenants** and suffix-matches the
  called number against `tenants.notification_phone`. No dedicated `twilio_number` column exists
  (grep confirms only env-level `settings.twilio_phone_number`, backend/config.py:43).
- **Mode switch (G3)** — `_ai_voice_mode` calls.py:54-58: `tenants.voice_ai_enabled`
  (migrations/143_voice_ai_enabled.sql) AND plan in `_AI_VOICE_PLANS = {"agent_os", "professional", "enterprise"}` (calls.py:51).
- **Voicemail mode (default / lower plans)** — `<Record>` greeting via `_build_twiml_greeting`
  (backend/services/voice_twiml.py:29-40) → `/voice/recording-complete` (calls.py:583-765): lead
  find/create on `leads.client_id` (calls.py:634-661), call record insert, owner SMS notify
  (calls.py:706-716), `call.completed` webhook, Twilio transcription request (calls.py:731-763)
  → `/voice/transcription-complete` (calls.py:768-898) stores transcript JSONB + queues AI summary.
- **Live AI mode — real speech loop, not a stub** — `/voice/incoming` returns
  `<Gather input="speech">` + `<Say>` greeting (calls.py:296-307); `/voice/respond`
  (calls.py:324-580) saves turns to `chat_messages` (`session_id = call_{sid}`), loads compacted
  history, tenant info, `faq_entries`, vertical guidance (calls.py:461-490), calls Claude via
  `call_claude_messages` (model setting `voice_chat_model` default `claude-sonnet-4-6`,
  160 max tokens, 30s timeout, calls.py:509-524), replies `<Say voice="alice">` + next `<Gather>`.
  Hard cap `_MAX_VOICE_ROUNDS = 3` (calls.py:45), then goodbye + finalize.
- **Lead capture** — `_find_or_create_lead` (calls.py:61-91): phone-only lead with
  `areas_of_interest="Inbound phone call (AI answered)"`, created up front so hangups leave a trail.
- **Call finalization + summary pipeline** — `/voice/call-status` (calls.py:175-218) →
  `_finalize_ai_call` (backend/services/voice_call_summary.py:230-295): idempotent transcript
  persist, then `_generate_call_summary` (voice_call_summary.py:24-179): Claude JSON summary,
  sentiment, `action_items` inserts (high priority), and a missed-call text-back draft through
  the Agent OS approval flow (`backend/services/voice_recovery.py:52+`, os_threads/os_agent_runs,
  auto-send per G6 rules).
- **Webhook auto-sync** — `backend/services/twilio_webhook_sync.py:54-119` points every account
  number at `/voice/incoming` + `/voice/call-status` from the 30-min automation loop
  (backend/main.py:347,415). No console config needed.
- **Dashboard API (backend only)** — list/stats/detail endpoints calls.py:906-1052. **No frontend
  code calls `/api/v1/calls`** (grep of frontend/src: zero hits; only analytics `missed-calls`
  in frontend/src/utils/api/analytics.js:44).
- **Settings toggle UI** — `frontend/src/pages/settings/MessagingSettingsCards.jsx:495-527`
  "AI Phone Answering" card with save flow.
- **Tests** — backend/tests/test_voice_incoming_call.py (11 tests: TwiML validity, voicemail vs
  AI branch, DB-failure resilience), backend/tests/test_voice_plan_gate.py (7 tests: agent_os in,
  chatbot/free out, grandfathered honored), tests/test_calls.py (36), tests/test_voice_prompt_contract.py (7).

## 2. What is missing

1. **BUG — frontend plan gate excludes `agent_os`**: MessagingSettingsCards.jsx:496
   `planEligible = ["professional", "enterprise"].includes(plan)` vs backend calls.py:51 including
   `agent_os`. Current-plan customers see the toggle permanently disabled. One-line fix.
2. **No appointment booking in the call path.** `propose_appointment` exists nowhere in the repo.
   The system prompt (calls.py:492-500) instructs the AI to *promise a human callback* for
   appointment requests. `backend/services/booking.py` (`get_business_hours`:33,
   `generate_available_slots`:90, `create_appointment`:215) is never imported by any voice module.
3. **3-round hard cap** (calls.py:45) — conversation dies after 3 caller turns; not per-tenant configurable.
4. **No streaming/realtime voice.** Zero `<Stream>`/websocket/media-stream code in backend (grep
   confirmed). Batch Gather loop means dead air while Claude responds (timeout 30s) and robotic
   `alice` TTS — the quality gap vs Phonely/Drillbit-class receptionists.
5. **No per-tenant number provisioning.** No number purchase flow, no `twilio_number` column;
   routing via `notification_phone` suffix match with a `limit(50)` tenant scan (calls.py:152) —
   breaks silently at tenant #51 and on shared last-10-digit collisions.
6. **No minutes metering/billing.** `duration_seconds` is stored per call but never aggregated,
   capped, or billed; `ai_usage_guard` covers tokens only. Twilio per-minute + Claude cost per
   call is unbounded per tenant.
7. **No calls dashboard page.** Backend list/stats/detail endpoints are orphaned — owners cannot
   see transcripts, recordings, or summaries anywhere in the UI.
8. **Tenant KB not used in voice prompts.** Voice uses `faq_entries` + vertical guidance only
   (calls.py:461-490); widget chat additionally grounds on `widget.knowledge_base` +
   `_query_kb_articles` (backend/routers/widget_chat.py:51,624-858). Voice answers are shallower
   than widget answers for the same tenant — undermines the KB moat.
9. **No lead enrichment from the call.** Caller name/details spoken mid-call never backfill the
   lead row; summary pipeline updates `calls` only (voice_call_summary.py:109-125).
10. **No answering-hours window, human transfer/escalation (`<Dial>`), barge-in, or outbound calls.**

## 3. Recommended build plan

- **Phase 0 (S) — unblock + expose.** Fix MessagingSettingsCards.jsx:496 to include `agent_os`
  (+ test in test_plan_gating_new_plans.py pattern). Ship `CallsPage.jsx` consuming existing
  calls.py:906-1052 endpoints (list, stats, transcript detail, recording link). Highest value per
  effort; makes the existing pipeline visible/sellable.
- **Phase 1 (M) — booking + lead capture in the loop.** Intent detection in `/voice/respond`
  (deterministic keyword pass, then structured extraction like widget_booking.py's marker-JSON
  pattern) → reuse `booking.generate_available_slots` to offer 2-3 slots aloud →
  `booking.create_appointment` (double-booking EXCLUDE constraint already on appointments table).
  Extract caller name from transcript in `_finalize_ai_call` and backfill the lead. Raise round
  cap to a per-tenant setting (llm_runtime settings pattern already used at calls.py:429-430).
- **Phase 2 (M) — number provisioning + routing hardening.** Migration: `tenants.twilio_number`
  (indexed, unique). Provisioning endpoint using Twilio `AvailablePhoneNumbers` +
  `IncomingPhoneNumbers` POST (auth pattern exists in twilio_webhook_sync.py:68-93). Replace the
  limit(50) scan with an exact-match indexed lookup (keep suffix match as fallback).
- **Phase 3 (M) — minutes metering.** Aggregate `duration_seconds` into the existing
  `tenant_usage_packs` machinery (see backend/tests/test_two_plan_repricing.py:365) with a monthly
  included-minutes allowance per plan + overage; guard in `/voice/incoming` (over-cap → voicemail
  mode, never a dropped call).
- **Phase 4 (L) — realtime upgrade.** Twilio ConversationRelay / Media Streams websocket +
  streaming STT/TTS to kill dead air and replace `alice`. This is a new service, not an edit to
  calls.py. Do it only after Phases 0-3 prove demand.
- **Riskiest unknown:** Gather-loop latency in production — Claude p95 + Twilio speech recognition
  per round vs caller hang-up tolerance. Measure via existing `timing_summary` logs (calls.py:574-579)
  on real calls before deciding whether Phase 4 is required for launch or a v2.

## 4. Decision points for the owner

- **Plans:** Is live voice `agent_os`-only forever, or a paid add-on for `chatbot`? Backend gate
  set (calls.py:51) and copy in the settings card must agree once decided.
- **Pricing model:** included minutes + per-minute overage vs flat? Raw cost ≈ Twilio inbound
  ~$0.0085/min + number ~$1.15/mo + ~1-2¢ Claude per call — GHL/competitors charge $0.10-0.30/min.
- **Number strategy:** platform-provisioned numbers (we pay Twilio, clean routing) vs customers
  forwarding their existing line (zero provisioning, but caller-ID and routing ambiguity).
- **Round cap / call length:** 3 rounds is a cost guard today; raising it changes per-call economics.
- **Voice quality bar:** ship on `alice` + Gather (fast) or hold G3 marketing until the streaming
  rewrite (Phase 4)? Competitors are benchmarked on latency and naturalness.
- **Compliance:** call recording consent ("this call may be recorded") is not in the greeting —
  two-party-consent states need it before wide rollout.
