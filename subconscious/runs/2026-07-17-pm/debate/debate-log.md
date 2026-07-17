# Debate Log — Run 98 (2026-07-17-pm)

Top 3 ideas by impact: Step 9F (Idea 1), conversation_enrichment scheduling (Idea 2), kb_hybrid pilot (Idea 3).

---

## Idea 1: Step 9F Carry-Forward — KB Staleness Check in nightly SKILL.md

### Challenge Round 1: Evidence strength
KB last ran 2026-07-13 — only 4 days ago, within the 7-day threshold. Step 9F would execute and report "healthy" for the next 3 days without firing any alert. What's the immediate value of implementing an alerting system that won't alert for 3 days?

### Defense Round 1
Step 9F was selected as run 97 winner precisely because the next gap is unpredictable, not because an alert is due tomorrow. The 72-day gap that motivated this idea happened silently — no signal fired between 2026-05-05 and 2026-07-09. Step 9F provides daily logging of KB staleness even when healthy ("Step 9F: KB autopopulate last run: 2026-07-13 (4 days ago)") — this is observability, not just alerting. The mandate from run 97 fires unconditionally. Steps 9B/9C/9D/9E were all implemented in 1 nightly cycle each via the same channel.

### Challenge Round 2: Is mandate check the right driver?
The mandate is self-referential — run 97 picked Step 9F, run 98 checks if it was implemented, run 98 picks it again if not. Is this a signal that something more valuable exists? PR #471 landed today with major new capabilities. Should run 98 pivot to something with more immediate impact?

### Defense Round 2
The mandate check fires because Step 9F is genuinely the right recommendation — it closes a known gap with proven mechanism. PR #471 is exciting but its features are opt-in and need validation before subconscious recommends enabling them broadly. Step 9F is XS effort, HIGH confidence, AUTONOMOUS-EXECUTABLE. This is a 3-minute SKILL.md edit that fires tonight and provides value for years.

### Challenge Round 3: KB autopopulate itself might not be working
GH #403 is still open. The kb-autopopulate.yml GitHub Actions workflow was created but its success depends on secrets (ANTHROPIC_API_KEY, SUPABASE_ACCESS_TOKEN) being configured. The 2026-07-13 KB run was a manual proof run — does the automated workflow actually run successfully?

### Defense Round 3
Valid concern. But Step 9F is precisely designed to surface this — if kb-autopopulate.yml keeps failing silently, Step 9F creates daily pressure on GH #403. The 7-day threshold means if the workflow fails again after 2026-07-13, Step 9F fires on 2026-07-20. This is the right mechanism for exactly this scenario.

**Verdict: SURVIVES → WINNER**

Step 9F carries forward as the correct recommendation. Mandate check 1 fails. XS effort. Proven mechanism. Daily observability value even when healthy.

---

## Idea 2: File GH Issue for conversation_enrichment_job.py Scheduling

### Challenge Round 1: Is this a real gap?
`conversation_enrichment_job.py` — what exactly does it enrich? The file name suggests conversation-level enrichment (tagging, categorization, quality signals?). Without reading the file, we don't know if this is production-critical or experimental infrastructure. Recommending scheduling without knowing what it does is premature.

### Defense Round 1
The enrichment job was explicitly named as "the first wired caller" of `batch_runtime.py` in the PR. batch_runtime.py has 236 test lines and full SDK verification. conversation_enrichment_job.py has 197 test lines. This is production-ready infrastructure, not experimental. The purpose is enriching conversations with AI analysis at 50% cost vs real-time.

### Challenge Round 2: Scheduling risk
A new cron job that runs AI on all conversations could have unexpected cost or latency impacts. What's the scale? How many conversations exist? If it processes all historical conversations, it could be expensive.

### Defense Round 2
batch_runtime.py is explicitly designed for offline, async, cost-optimized work with a 24h processing window. The enrichment job is designed to run on a scheduler tick — it wouldn't process all history in one run. But this concern is valid — without knowing the exact `WHERE` clause in the job, recommending a GH issue rather than direct implementation is the right approach. The GH issue itself creates no risk.

### Challenge Round 3: Priority against Step 9F
GH #399 is still open — issue-to-pr-loop can't pick up ai-ready issues anyway. Filing a GH issue now means it sits in queue behind 30+ other ai-ready issues. Low immediate impact.

### Defense Round 3
Conceded. Even as a GH issue, this competes with 30+ queued items behind GH #399. Better to park this until GH #399 is resolved and the queue clears.

**Verdict: WEAKENED → Parking lot**

Good idea, wrong timing. GH #399 blockage means any new ai-ready issue has low expected execution time. Park until GH #399 resolved. Priority: LOW until then.

---

## Idea 3: Enable kb_hybrid_retrieval for Keys Koffee Pilot

### Challenge Round 1: Evidence strength
kb_hybrid_retrieval.py shipped today (PR #471, 2026-07-17). Zero production usage history. Recommending enabling a new feature on the same day it ships — is that evidence-backed or premature?

### Defense Round 1
kb_hybrid_retrieval.py is fail-open by design: "any error in the FTS pass returns the caller's `semantic_rows` unchanged. A broken hybrid merge must never break KB grounding." The risk is zero — worst case, it degrades to current behavior. Keys Koffee coffee FAQ with "do you have oat milk" is a documented keyword query that hybrid would improve.

### Challenge Round 2: Mechanism blocker
Enabling requires a Supabase UPDATE on `widget_configs`. Supabase MCP is unavailable in headless/cron sessions — confirmed in run 88 governance corrections. This would need to be a human-action GH issue, which again competes with GH #399 queue.

### Defense Round 2
This is a valid blocker. The human-action GH issue path would sit unfiled or unactioned. Keys Koffee's most urgent need right now is getting business hours configured (GH #415, still open Day 24+) — that's a higher-priority human action. Adding a widget_configs toggle GH issue adds noise when attention is already stretched.

### Challenge Round 3: Is there a higher-priority kb_hybrid use case?
kb_hybrid_retrieval.py is opt-in. Who decides to enable it? The tenant? The admin? Without a UI to toggle it, enabling requires a SQL update. This is infrastructure that needs a settings UI before it's operationally viable. The current path (SQL update GH issue) is temporary scaffolding.

### Defense Round 3
Conceded. The right next step for kb_hybrid is a settings toggle in the admin dashboard, not a one-off SQL update. This belongs after a Settings UI is built for new widget_configs options. Park for now.

**Verdict: WEAKENED → Parking lot**

Wait for: (1) Settings UI for new feature flags, or (2) GH #399 resolved so issue-to-pr-loop can implement the settings toggle. Park as "kb_hybrid enable — pending settings UI or GH #399."

---

## Synthesis

| Idea | Verdict | Notes |
|---|---|---|
| Step 9F KB staleness check | **SURVIVES → WINNER** | XS effort, proven mechanism, mandate fires |
| conversation_enrichment scheduling | WEAKENED → parking lot | Good idea, GH #399 blocks execution queue |
| kb_hybrid pilot tenant | WEAKENED → parking lot | Needs settings UI or GH #399 first |
| notify_common failure-mode check | — (not debated) | Mandate closure: safe_send_email swallows by contract, effectively resolved |
| BotHealthPage.jsx frontend | — (not debated) | L-effort, GH issue filed, post-queue backlog |
