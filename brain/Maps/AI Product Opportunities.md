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

## Priority read (unified, both rounds)
**Do first / cheap + high:** #F1 Sonnet 5 swap → #F3 structured outputs (kills a live bug class) → #R7 cost-floor
plumbing. **Highest strategic value (the moat):** #F2 contextual retrieval + reranker, then #R5 GEPA per-tenant
compounding. **Biggest new revenue:** #R1+#R2 photo-triage + instant quoting (attacks Drillbit on our own front
door). **Best new margin SKU:** #R3 GEO add-on. **Strongest retention lever:** #R4 Bot-Health evals (also the
prerequisite for #R5). **Match-competitor:** #R6 reactivation outbound + expose voice model/language selection
(GHL parity) + RCS via Twilio. **Bigger bet / watch:** #F7 streaming voice. **First housekeeping step:** re-audit
model IDs in `.claude/rules/model-routing.md` + CLAUDE.md against Opus 4.8 / Sonnet 5 (this session runs on Opus 4.8).

## Related
- [[Chat Widget]] · [[Agent Service]] · [[Knowledge Base Wiki]] · [[Vertical Knowledge-Base Moat]] · [[GoHighLevel]] · [[G3 voice live-answering]] · [[Cold Outreach Engine]]

## Provenance
- Web research this session (2026-07-13). Source URLs inline per item. Claims are vendor/blog
  reported figures — treat directional, validate against our own funnel before quoting to customers.
