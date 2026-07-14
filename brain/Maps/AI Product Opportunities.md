---
type: map
name: "AI Product Opportunities"
tags:
  - map
  - moc
  - product
  - ai
source_status: source-backed
sensitivity: normal
last_updated: 2026-07-14
---

# AI Product Opportunities

Web-sourced AI innovations mapped to concrete AgentNexLiFy product moves. Scope: things
the **widget / agent / booking / follow-up** could adopt to win more leads and close more
bookings. Each item is what-it-is → how-we-use-it → source. Reviewed 2026-07-13.

## 1. Proactive, behavior-triggered chat (biggest near-term lever)
Chatbot-led funnels convert at ~2.4x static web forms (15-30% vs ~2%), and responding within
5 minutes lifts conversion odds up to ~900%. The trigger is behavioral: time-on-page, scroll
depth, exit intent (cursor leaving to close the tab), and campaign source. Our [[Chat Widget]]
is currently **reactive** — the visitor has to open it. Adding proactive triggers (open with a
vertical-specific prompt on exit-intent or after N seconds on a service page) is a small widget
change with an outsized conversion payoff, and it needs no model upgrade.
Source: https://www.fwdslash.ai/blog/how-ai-chatbots-improve-website-conversion-rates

## 2. In-chat lead qualification + scoring
The strongest lead bots qualify in-conversation with BANT (budget, authority, need, timeline)
or a custom rubric, then sort hot/warm/cold before a human sees them. We already capture leads;
adding a lightweight qualifier (reuse the `lead_qualifier` managed agent) to score and route
means the tenant's phone lights up for hot leads first. Pairs with the widget's existing
[[Agent Service]] flow — score on capture, not in a nightly batch.
Source: https://www.ringover.co.uk/blog/lead-generation-chatbot

## 3. AI appointment reminders + smart rebooking (direct revenue)
A two-reminder cadence (24h + 1-2h before) cuts no-shows ~45-50%; one peer-reviewed set of
135k appointments dropped no-shows 20.8% → 10.3%. SMS is preferred by ~78% of customers, and
"smart rebooking" auto-fills a cancelled slot from a waitlist. We already book to Google
Calendar and have Twilio wired — this is an automation build, not new infra. Concrete: a shop
doing 100 appts/mo at $150 recovers ~$23k/yr by moving no-shows 25% → 12%. This is a headline
number for the [[MTOptions]] case study and a sellable `agent_os` feature.
Source: https://www.famulor.io/blog/ai-appointment-reminders-cut-no-shows-by-50-in-2026

## 4. Better per-tenant retrieval = the moat, upgraded
Our edge is the [[Vertical Knowledge-Base Moat]] — per-tenant [[Knowledge Base Wiki]] answers,
not generic LLM replies. 2026 retrieval techniques push domain accuracy to 95-98% with
near-zero hallucination: **context-graph-grounded RAG** (structure retrieved knowledge as a
graph, not flat chunks) beats single-retrieval by 20-35%, and **multi-evidence RAG** cut
hallucinations 8% → 0 in one study. Our retrieval today is flat pgvector chunks; moving to
graph-grounded retrieval + a confidence threshold that escalates low-confidence answers to a
human is the highest-leverage quality upgrade to the core product. Wrong answers on a tenant's
site are the fastest way to lose them, so accuracy is a retention lever, not just a demo metric.
Source: https://www.kernshell.com/how-rag-reduces-ai-hallucinations-and-improves-accuracy/

## 5. Voice as a receptionist add-on
Voice-agent latency crossed sub-300ms in 2026 (native-audio models + ~90ms TTS), making live AI
phone answering production-ready. This resolves the feasibility blocker on [[G3 voice
live-answering]] and answers the voice-first competitors ([[Phonely]], GHL Voice AI). Reuse the
tenant KB + booking engine behind a native-audio agent; MCP (already in our stack) is becoming
the standard connective layer. See [[ai-voice-agents-sub-300ms-2026]] in the wiki for depth.
Source: https://flowful.ai/blog/voice-agents-2026/

## 6. Competitor signal — GoHighLevel AI Employee (what to match)
[[GoHighLevel]] shipped "AI Employee" as five tools (Voice, Conversation, Reviews, Content,
Funnel) at $97/mo on top of the platform. Three moves worth matching or countering:
**Reviews AI** (auto-request + respond to reviews — a clean `agent_os` add), **scheduled AI
prompts with a human-approval step** (recurring automation that never fires without sign-off —
mirrors our own drafts-only approval loop), and **multi-language call transcription** (10
languages) — a real wedge for multilingual SMB communities we don't yet serve. GHL also cut
Conversation-AI latency ~40% to sub-2s replies, which sets the response-speed bar our widget
must meet. Source: https://netpartners.marketing/gohighlevel-ai-employee/

## Shipped 2026-07-14 (PR #411, merged to main)
Items 1, 2, 3, 5, 6 above went from opportunity to production in one pass:
- **#1 proactive triggers** — `widget_configs.proactive` jsonb (migration 169); default off; live on our own tenant.
- **#2 in-chat scoring** — lead scoring now runs synchronously on capture, not in a nightly batch.
- **#3 reminders** — `appointment_reminders` table (migration 167) + per-tenant opt-out; the live legacy 24h+1h sender now honors the toggle.
- **#5 voice grounding** — voice calls inject top-3 tenant KB articles into the prompt (the KB-grounding half of the voice opportunity; low-latency audio stack is still open — see frontier #F7 below).
- **#6 reviews AI** — approval-gated `review_responses` drafting (migration 168); drafts only, posting stub pending per-platform integration.
Still open from the original list: **#4 graph/better retrieval** (the moat upgrade) — now sharpened by frontier #F2 below.

## Shipped 2026-07-14 (PR #431)
Round-2/frontier items built in one pass:
- **#F1 Sonnet 5 swap** — widget + voice default to `claude-sonnet-5`; `_requires_sampling_omission` extended to the reasoning-tier models so the swap doesn't 400 the widget. Model-ID docs refreshed to Opus 4.8 / Sonnet 5.
- **#R4 Bot-Health evals** — `bot_health_scores` table (migration 170) + Haiku LLM-as-judge service + `GET /api/v1/bot-health/{tenant_id}` + admin `/run`.
- **#R1+#R2 photo-triage + quoting** — `photo_triage.py` (vision) + `quote_builder.py` (catalog-grounded, hard "never invent prices") + migration 171 + endpoints + widget triage-on-upload.
Deferred (flagged): re-baseline `PLAN_BASELINE_TOKENS` for Sonnet 5's tokenizer; cron-wire the Bot-Health sweep; dashboards for both.

## Shipped 2026-07-14 (PR #431, round-3 items — merged to main, live in prod)
Compliance + ops items built + merged:
- **CR1/CR4 voice disclosure** — AI-identification + recording notice in the AI-call greeting (before first prompt) + recording notice in the voicemail greeting. Non-disableable, regression-tested.
- **CR5 chatbot disclosure** — already shipped in the widget greeting; verified, no change.
- **#T2 attribution** — migration 172 (`leads.attribution jsonb`, applied prod); widget captures first-touch utm/referrer/landing_path/source; stored via the LIVE chat capture path (`_capture_leads_from_session`) + explicit form; first-touch only; `attribution.py` sanitizer.
- **#T3 injection guard** — `widget_guard.py` (Haiku screen, fail-open) + per-session turn budget, wired into `widget_chat` before the Sonnet call.
- **#T4 LLM fallback** — opt-in `fallback_models` + `graceful_reply` in `llm_runtime`; default behavior unchanged.
- **#T1 auto-onboarding** — already ships as `instant_kb.py` (`/api/v1/instant-kb/{tenant_id}/draft` + `/confirm`, SSRF-checked); no duplicate built.
Still deferred (need external creds): CR2/CR3 A2P status (Twilio Messaging Service), #T5 FSM OAuth (Jobber/QuickBooks/ServiceTitan), #T6 Stripe usage metering.

## Frontier update 2026-07-14 (model stack is ~2 generations stale)
**Critical:** CLAUDE.md / `.claude/rules` still pin `claude-opus-4-7` + `claude-sonnet-4-6` as newest.
Anthropic shipped **Opus 4.8** and **Sonnet 5** on 2026-06-30. The whole model-routing surface is stale
and should be re-audited (this session's own runner is Opus 4.8). Web research 2026-07-14, sources inline.

- **#F1 — Sonnet 5 for widget chat (do first).** Near-Opus reasoning/tool-use at Sonnet cost; intro
  pricing $2/$10 per M through 2026-08-31. Swap `claude-sonnet-4-6` → `claude-sonnet-5` in the widget
  runtime = smarter *and* cheaper lead-capture. Re-baseline `ai_usage_guard.PLAN_BASELINE_TOKENS` — new
  tokenizer maps text to 1.0–1.35× more tokens. Effort S / Impact High.
  Source: https://www.anthropic.com/news/claude-sonnet-5
- **#F2 — Contextual Retrieval + reranker (the moat play).** Prepend a 50–100 tok context blurb per chunk
  before embedding + hybrid BM25 + a rerank pass. Measured −35% / −49% / **−67%** failed retrievals as you
  stack the three. Fits our pgvector [[Knowledge Base Wiki]] directly; this is the concrete form of the
  old item #4. Effort M / Impact High.
  Source: https://www.anthropic.com/engineering/contextual-retrieval
- **#F3 — Structured Outputs + strict tool use.** JSON-schema-constrained sampling (`output_config.format`,
  `strict:true`). Kills malformed-JSON / silent-data-loss in the `lead-extractor` + `lead-qualifier` +
  appointment-capture paths — the exact bug class our schema-discipline rules guard. Effort S–M / Impact High.
  Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- **#F4 — Per-tenant prompt caching (1-hr) + Batch API.** Every widget turn re-sends the tenant KB + persona;
  cache it per-tenant → cache-read ≈10% of input cost. Route non-interactive jobs (review drafts, KB
  autopopulate, scoring backfills) to the Batch API for 50% off. Not for the live latency path. Effort S–M / Impact High.
  Source: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- **#F5 — Memory tool + context editing.** GA `memory_20250818` gives cross-session state (~84% token savings
  on long runs) for [[Agent Service]] background agents + multi-day follow-up sequences. Effort M / Impact Med–High.
  Source: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- **#F6 — Layered hallucination guardrails + citation-enforced answers.** Sub-200ms inline "is this answer
  supported by the retrieved chunks?" check before send + a 5–20% async eval cohort feeding a per-tenant
  quality dashboard; force the bot to cite its KB chunk or deflect ("I don't have that — want someone to
  follow up?", itself a lead-capture moment). Pairs with #F2. Effort M / Impact High.
  Source: https://futureagi.com/blog/llm-hallucination-deep-dive-2026/
- **#F7 — Streaming speech-to-speech voice (the competitive gap).** Phonely/GHL/Podium voice is near-real-time
  (p50 <250ms) via native-audio + ~90ms TTS (Cartesia Sonic-3) + streaming STT (Deepgram Nova-3). Our
  turn-based Claude+STT+TTS voice pipeline is likely 800–1500ms. Claude is text-only, so this is a separate
  low-latency audio layer with Claude as the reasoning brain. Effort L / Impact High (voice is where we're behind).
  Source: https://telnyx.com/resources/voice-ai-agents-compared-latency

## Competitor moves (refreshed 2026-07-14)
- **[[GoHighLevel]]** — 2026 cadence: AI Appointment Setter + Conversation AI → Voice AI → **AI Employee +
  RCS messaging** (May) → Workflow AI (June); sub-2s replies. **RCS is a concrete gap for us.**
  Source: https://www.gohighlevel.ai/blog/gohighlevel-updates-2026
- **Podium** — "AI Employee" (Jerry) with 5 roles + home-services voice agent; claims <1-min lead response →
  +45% sale odds. Source: https://www.podium.com/product/ai-employee
- **Phonely** — $16M Series A (~$100M val); **per-customer fine-tuned voice models** that compound per call.
  Their per-tenant moat rhymes with our per-tenant KB — differentiate on grounding breadth. Source: https://www.phonely.ai/blog/phonely-series-a-16m-funding
- **Drillbit (YC S24)** — AI receptionist + **LLM quoting engine** (job request → detailed quote in seconds)
  for residential trades. Vertical quoting is a capability we lack. Source: https://www.ycombinator.com/companies/drillbit

## Frontier round 2 — 2026-07-14 (new angles: vision, quoting, GEO, evals, compounding)
Second research pass into surfaces round 1 didn't cover. New revenue/retention SKUs, not just runtime tweaks.

- **#R1 — Photo-triage in the widget (vision → damage/scope).** Caller uploads 1–3 photos (burst pipe, roof,
  dent); Claude vision triages urgency + scope → routes to urgency-scored booking, attaches photo to the lead.
  Production-viable now (Tractable: 90% of auto estimates touchless, 98% <15 min). Surfaces: widget flow +
  multimodal `/api/chat` + `leads` photo/triage fields. Gate behind `agent_os` / a Vision add-on. Effort M / Impact High.
  Source: https://tractable.ai/ · https://myquoteiq.com/ai-estimator/
- **#R2 — AI instant-quoting engine (the Drillbit wedge).** Job request (text or #R1 photo) → itemized
  Good/Better/Best quote grounded in the *tenant's own price list/catalog* — a natural extension of our KB moat.
  Drillbit/Handoff/QuoteIQ do this standalone; we already own the multi-channel front door (widget + voice) they
  bolt onto. New "Quote Builder" surface; premium/metered tier. Effort L / Impact High.
  Source: https://www.handoff.ai/instant-ai-estimates · https://app.drillbit.com/
- **#R3 — GEO add-on SKU (get tenants cited in AI answers).** Distinct from our SEO addon: SEO ranks pages, GEO
  wins ChatGPT/Perplexity/Google-AI citations. AI search ≈12–18% of informational queries; agencies already sell
  this at **$500–2k/mo/client**. Ship citation-tracking dashboard + AI-citable content generator. Strongest new
  *margin* story. Effort M / Impact High.
  Source: https://www.enrichlabs.ai/blog/generative-engine-optimization-geo-complete-guide-2026
- **#R4 — Per-tenant Bot-Health evals (the retention layer).** LLM-as-judge on ~100% of tenant traffic —
  resolution rate, hallucination flags, unresolved-intent clusters, sentiment trend — with a "your bot is
  degrading / KB gap detected" alert. Turns silent churn into a dashboard signal + upsell. Cheap to run
  continuously via #F4/#R7. Ties to the `churn-prevention` skill. Effort M / Impact High.
  Source: https://www.confident-ai.com/knowledge-base/compare/best-ai-agent-observability-tools-2026
- **#R5 — GEPA per-tenant prompt compounding (no fine-tuning).** Reflective prompt evolution (ICLR 2026 Oral):
  optimize each tenant's system prompt from its own resolved/escalated conversations + the #R4 eval scores —
  beats RL by ~20% at ~35x fewer rollouts, weights frozen, no per-tenant GPU. This is "each tenant's agent gets
  smarter for free" (Phonely's moat, prompt-side). Offline job → `widget_configs`. Depends on #R4. Effort L–M / Impact High.
  Source: https://arxiv.org/pdf/2507.19457 · https://github.com/gepa-ai/gepa
- **#R6 — Reactivation / no-show win-back (outbound).** Dormant-contact detector → AI-personalized SMS/email →
  booking, on the `leads`/`appointments` data we already hold. A headline GHL/agency feature we can match
  natively. `agent_os`-tier expansion. Effort M / Impact High (figures vendor-reported, directional).
  Source: https://octavius.ai/ai-sms-for-database-reactivation/
- **#R7 — Cost floor that makes #R4/#R5/#R6 margin-safe.** Haiku 4.5 $1/$5 per M, cached reads 0.1x, Batch 50% off,
  and they stack. Route all always-on eval/optimization/outbound through Haiku + cache + Batch; centralize in
  `llm_runtime.py`. Not a feature — the economic enabler for the round-2 bets. Effort S / Impact Med.
  Source: https://www.finout.io/blog/anthropic-api-pricing
- **#R8 — Vertical-as-Agent-Skill + MCP vertical data.** Model each vertical (plumber/dentist/roofer) as an
  Agent Skill (progressive-disclosure folder: KB + quoting rules + booking flow + tone) → deep vertical expertise
  without bloating every request. MCP connectors can feed authoritative pricing (Verisk-in-Claude pattern, ~May
  2026) to ground #R2. Operationalizes the moat as a reusable unit. Effort M / Impact Med–High.
  Source: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

## Competitor signals round 2 (2026-07-14)
- **[[GoHighLevel]] "Summer of AI" (July):** Voice AI moved to **GPT-5 Mini**, sub-600ms, **20+ accents +
  multilingual**, direct model selection. Our voice product should expose model/voice/language choice for parity.
  Source: https://netpartners.marketing/gohighlevel-voice-ai-promo-july-2026/
- **Twilio RCS GA:** branded messaging auto-upgrades SMS→RCS on capable devices at no extra cost; 20+ countries.
  Low-friction to add via our existing Twilio dependency (the RCS gap noted in round 1). Source: https://www.twilio.com/en-us/press/releases/rcs-general-availability
- **Verisk-in-Claude (~May):** vertical data vendors now ship MCP connectors into Claude — validates the
  "ground the agent in authoritative vertical data" thesis behind #R8/#R2.

## Frontier round 3 — 2026-07-14 (operations, GTM, compliance risk)
Rounds 1-2 were model capabilities. Round 3 = the operational/legal/GTM factors that decide whether the AI
features convert to revenue and don't cause legal/trust blowups. **All legal items: not legal advice — verify
with counsel.** Sources inline.

### ⚠️ Compliance risk register (launch-gating for voice + SMS — do FIRST)
The voice + SMS surfaces carry real, dated legal exposure. Ranked by urgency:
- **CR1 — AI voice consent + at-open disclosure.** FCC (Feb 2024) treats AI voices as "artificial" under TCPA →
  prior express consent + an AI-identification preamble at the START of every call. TX SB 140 (30-sec disclosure)
  + TX TRAIGA (Jan 1 2026) live. $500+/call; 2025-26 class actions settled $5-20M. **Hardcode a non-disableable
  AI-disclosure preamble on the Twilio voice line; log per call.** Source: https://www.fcc.gov/document/fcc-confirms-tcpa-applies-ai-technologies-generate-human-voices · https://www.retellai.com/blog/tcpa-compliance-playbook-voice-ai-outbound
- **CR2 — SMS consent. ⚠️ CORRECTED 2026-07-14 (round-4 research): the FCC "one-to-one consent" rule is DEAD, not live.**
  11th Circuit vacated it Jan 2025; FCC issued a final rule eliminating it Sept 2025. Standard reverted to the
  pre-2023 **prior express written consent** (signature + clear disclosures) with NO one-to-one requirement. The
  consent-revocation-all rule is delayed to **Jan 31 2027**. Prior "LIVE Jan 27 2026" claim was stale vendor-blog
  misinfo — do NOT build consent UX around a one-to-one requirement. Real gate = written consent + A2P 10DLC (CR3).
  $500-1,500/msg TCPA exposure still applies. Source: https://compliancehub.wiki/tcpa-2026-consent-revocation-one-to-one-rule-vacated-compliance/ · https://www.mofo.com/resources/insights/250130-eleventh-circuit-vacates-fcc-s-tcpa-one-to-one-consent-rule
- **CR3 — A2P 10DLC brand+campaign registration.** Carriers block 100% of unregistered traffic since Feb 2025.
  **Gate all outbound SMS on registration status.** (Turn registration into a paid, sticky onboarding step.)
- **CR4 — Call-recording all-party consent.** 12 all-party states; stricter-law-wins across state lines. **Default
  the strict-state recording notice on every recorded call** (caller state unknown at pickup). Source: https://www.getnextphone.com/blog/call-recording-laws-by-state
- **CR5 — Chatbot "you're talking to AI" disclosure.** EU AI Act Art. 50 (Aug 2 2026, EU visitors only) + growing
  US state patchwork. Greeting lives in DB (`widget_configs.greeting_message`) — **enforce a non-removable AI
  disclosure at render, not via tenant-edited text.** Source: https://artificialintelligenceact.eu/transparency-rules-article-50/
- **CR6 — Prompt-injection / cross-tenant leak** (see #T3 below). A cross-tenant KB leak is trust-fatal.
- **Fastest wins (S effort):** CR4 recording notice + CR5 chatbot disclosure — both are hardcoded opening lines.

### Other round-3 findings
- **#T1 — Auto-onboarding: URL + Google Business Profile → grounded KB in minutes.** Now table-stakes (Oscar Chat,
  SiteGPT, Wonderchat auto-crawl in 5-15 min + auto-resync). Time-to-value is the #1 SMB churn driver. Build a
  self-serve: tenant enters URL + GBP → crawler + Claude compile the per-tenant KB + draft FAQ (fits our
  `knowledge-base/` + pgvector) → tenant reviews, not authors. Highest-leverage GROWTH item. Effort L / Impact High.
  Source: https://www.oscarchat.ai/blog/knowledge-base-ai-chatbot-2026/
- **#T2 — Closed-loop attribution + ROI dashboard.** Capture source/UTM/tracked-DID per session + voice call;
  Claude writes a structured per-conversation outcome (fit, urgency, booked y/n, objection) to the record; surface
  "which campaign booked the appointment." The renewal/upsell justification lever AND the clean measurement
  substrate any outcome pricing needs. Effort M / Impact High. Source: https://thoughtly.com/blog/best-ai-voice-agent-platforms-pipeline-analytics-2026
- **#T3 — Prompt-injection defense-in-depth on the public widget.** OWASP #1 LLM threat. Haiku cheap-probe gate →
  Sonnet answer; strict output-schema validation; per-IP/session rate + token caps; treat KB content as DATA not
  instructions (defends indirect injection via poisoned crawled pages from #T1). Protects tenant isolation
  (`client_id`), brand safety, and margin at once. Effort M / Impact High. Source: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html · https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks
- **#T4 — Multi-provider LLM fallback gateway.** Anthropic logged 114 incidents / 90 days, and a June 12 2026
  Commerce order suspended two models for all customers. A dead widget/voice line on the TENANT's site/phone is
  worse than a normal outage. Put LiteLLM in front of `llm_runtime.py`: ordered fallback (Sonnet 5 → secondary
  provider → cached canned reply); tightest on voice (dead air is unrecoverable). Incident path, not routine, so
  it doesn't violate the mid-session cache-hygiene rule. Effort M / Impact High. Source: https://www.deepinspect.ai/blog/llm-fallback-routing
- **#T5 — FSM integrations = purchase gate for trades.** Table-stakes: two-way Google/Outlook Calendar, then one
  FSM (Jobber is the SMB-friendly entry) + QuickBooks; Zapier as interim bridge. NOTE: Jobber + Housecall Pro now
  ship their OWN AI receptionists → compete by being cross-platform (works for tenants not on one FSM). Effort L /
  Impact High. Source: https://www.pinkcallers.com/blog/servicetitan-vs-jobber-vs-housecall-pro-for-call-center-integration
- **#T6 — Hybrid / outcome pricing.** Flat $19.99/$99.99 leaves value on the table. Market split: bundle basic
  widget chat free (Birdeye-style), METER the expensive surfaces — voice minutes, per-booked-appointment outcomes
  (Intercom Fin $0.99/resolution, Zendesk $1.50, 11x per-meeting; hybrid = 43%→61% of SaaS, +38% growth). Needs
  clean measurement (#T2) as the billing substrate; Stripe's Metronome buy means metering is buy-not-build. Effort
  M (packaging) + L (metering) / Impact High. Source: https://www.getmonetizely.com/blogs/the-2026-guide-to-saas-ai-and-agentic-pricing-models

### Competitor signals round 3
- **[[GoHighLevel]]** unbundled ALL AI into paid add-ons: "AI Employee" $97/mo/sub-account (unlimited) OR
  ~$0.02-0.05/min usage; Voice AI per-minute; Conversation AI token-based. Direct comp for our `agent_os` ($99.99)
  — match the "unlimited" framing or win on lower friction (widget-first, #T1 onboarding). Source: https://help.gohighlevel.com/support/solutions/articles/155000006652-ai-product-pricing
- **Birdeye** bundles BirdAI free into every tier → sets a floor that basic chat AI shouldn't be a line item
  (supports keeping widget chat in the base `chatbot` plan, metering only voice/outcomes).
- **Jobber + Housecall Pro** shipped their own AI receptionists → the FSM incumbents are now competitors; our wedge
  is cross-platform + widget-first.

## Priority read (unified, all three rounds)
**⚠️ Do BEFORE any voice/SMS launch (legal):** the CR1-CR5 compliance gate — AI-voice disclosure preamble,
all-party recording notice, named-brand SMS consent + 10DLC gate, non-removable chatbot AI disclosure. Cheapest
+ most urgent: CR4 + CR5 (hardcoded opening lines). *Verify with counsel.*
**Do first / cheap + high (already partly shipped):** ~~#F1 Sonnet 5~~ ✅ → #F3 structured outputs → #R7/#T3
cost-floor + injection gate (same Haiku-probe pattern).
**Highest-leverage growth:** #T1 auto-onboarding (URL+GBP → KB) — collapses time-to-value, the #1 churn driver.
**Strongest retention/upsell:** #T2 attribution ROI dashboard (also the substrate for #T6 outcome pricing) +
~~#R4 Bot-Health~~ ✅.
**The moat, deepened:** #F2 contextual retrieval + reranker → #R5 GEPA per-tenant compounding.
**Reliability gate for voice:** #T4 multi-provider fallback.
**Revenue/packaging:** #T6 hybrid (bundle chat, meter voice/outcomes) + #R3 GEO add-on.
**Trades purchase gate:** #T5 calendar + FSM + QuickBooks sync.
**Bigger bet:** #F7 streaming speech-to-speech voice.

## Frontier round 4 — 2026-07-14 (cost/reliability infra + pricing pressure)
Two research passes (frontier API + competitive/GTM). Full source URLs in the session; key finds:

### Frontier API (cost + reliability, mostly S-effort)
- **#F8 — Prompt caching on the tenant KB+persona prefix (SHIPPING THIS ROUND as #F4).** Widget re-sends the full
  tenant system prompt every turn; `cache_control` on that stable block bills cache reads ~0.1x. Opus 4.8 dropped
  the cache floor to 1,024 tokens so even small tenant prompts qualify. Single biggest cost lever. Effort S / Impact High.
- **#F9 — Structured Outputs GA (`output_config.format`, no beta header).** Guaranteed schema conformance on
  Sonnet/Opus/Haiku. Replaces hand-rolled JSON parse + retry in `lead-extractor`, `lead-qualifier-prod`,
  `widget-support`, and the `ai-feature-pattern` JSON-repair path. Reliability win. Effort S–M / Impact High.
- **#F10 — Reranker on top of pgvector (Voyage rerank-2.5 / Cohere Rerank 4 / Zerank-2).** 2026 standard =
  hybrid retrieve top-50 → cross-encoder rerank → top-5. +15–30% answer quality, one API call, no infra change.
  Direct upgrade to the cosine-only KB retrieval — deepens the vertical-KB moat. Effort S / Impact High.
- **#F11 — Batch API (50% off, <1hr).** Move all non-realtime Claude calls here: nightly email/sequence
  generation, KB auto-populate compile, eval runs, lead re-scoring. Halves offline spend, zero product change. Effort S / Impact Med–High.
- **#F12 — Hybrid retrieval in one fused SQL (pgvector + tsvector/pg_trgm BM25, RRF) + contextual chunk prefixes.**
  Pairs with #F10. `reindex_contextual.py` already scaffolded. Effort M / Impact High.
- **Free wins:** no-charge refusals (June 2), `response_inclusion` to drop consumed web-fetch blocks, native
  Advisor tool (replaces hand-rolled `advisor_executor.py` two-call flow). Effort S each.
- **Migration landmines before any model bump:** Sonnet 5 / Opus 4.7-4.8 reject non-default `temperature`/`top_p`/`top_k`
  with a 400 (grep runtime first — already guarded by `_requires_sampling_omission`); Sonnet 5 tokenizer ~+30% tokens
  (recompute cache/batch/`max_tokens` math + re-baseline `PLAN_BASELINE_TOKENS`).

### Competitive / GTM (pricing is the pressure)
- **GoHighLevel "Summer of AI" (Jun 1–Aug 31 2026):** 5 AI tools free for every paid sub-account + 30-day free
  Conversation/Voice AI + $100K contest. $97/mo *unlimited* omnichannel AI Receptionist straddles both our tiers.
  **Active trial-poaching window through Aug 31.** Wedge = widget-first + zero-setup + per-tenant vertical KB.
- **Jobber AI Receptionist:** $29/mo (30 convos, then $0.79/convo), 200K+ convos, bundled in the trades CRM.
  **Housecall Pro:** CSR AI free in Essentials/MAX. FSM incumbents now bundle AI receptionist → undercut our trades ICP.
  Our lane = businesses NOT on a vertical FSM platform (salons, dentists, local services).
- **Pricing direction = hybrid + outcome.** Intercom Fin $0.99/resolution, Zendesk $1.50–2.00/resolution;
  43%→61% of SaaS going hybrid (base + usage). Our flat $19.99/$99.99 sits at the bottom band ("lite" signal, money
  left on table). **#T6 refined:** keep the $19.99 hook, add a conversation/booking metered overage + an
  outcome-metered agent_os option (per booked appointment / qualified lead) — strongest differentiator vs GHL flat + Jobber per-convo.
- **EU AI Act Art. 50 chatbot disclosure binding Aug 2 2026** (EU-facing traffic) — we ALREADY ship CR5 in the
  widget greeting ✅, so we're ahead. **A2P 10DLC** blocks 100% of unregistered traffic + AI SMS must match approved
  templates → gate SMS activation on registration. **AI-voice disclosure** (CA AB2905 + TX TRAIGA live) — CR1/CR4 shipped ✅.
- **⚠️ Correction:** FCC SMS one-to-one consent rule is DEAD (vacated 2025) — see CR2 above, corrected this round.

### Priority read (round 4 — refreshed)
**Ship now, cheap + high (cost/reliability infra):** #F4 prompt caching (this round) → #F10 reranker → #F9 structured
outputs → #F11 Batch API. All S-effort, compounding cost/quality wins, no external creds.
**The moat, deepened:** #F10 reranker + #F12 hybrid/contextual retrieval → #R5 GEPA per-tenant prompt compounding (uses the shipped #R4 eval scores).
**Revenue/packaging (competitive response to GHL/Jobber):** #T6 hybrid metered overage + outcome-metered agent_os tier — needs Stripe metering (buy-not-build via Stripe Billing meters).
**Growth:** #T1 auto-onboarding already ships (`instant_kb`); surface it in the signup wizard as the time-to-value hook.
**Deferred (external creds):** #T5 FSM/calendar OAuth, CR2/CR3 A2P status surfacing, #T6 Stripe meter setup.

## Related
- [[Chat Widget]] · [[Agent Service]] · [[Knowledge Base Wiki]] · [[Vertical Knowledge-Base Moat]] · [[GoHighLevel]] · [[G3 voice live-answering]] · [[Cold Outreach Engine]]

## Provenance
- Web research across 4 passes (2026-07-13/14): round 1 model capabilities, round 2 new-angle product moves,
  round 3 operations/GTM/compliance, round 4 cost/reliability infra + pricing pressure. Source URLs inline per
  item. Vendor/blog figures are directional — validate against our own funnel before quoting to customers.
  **Legal items are NOT legal advice — verify with counsel before shipping voice/SMS. CR2 one-to-one consent
  claim was corrected in round 4 (rule is vacated, not live).**
