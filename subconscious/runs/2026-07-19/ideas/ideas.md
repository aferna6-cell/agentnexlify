# Run 2026-07-19 — Candidate Ideas

## Evidence Summary
- Step 9F (KB autopopulate staleness check) ABSENT for 3rd consecutive cycle. KB healthy (6 days, within 7-day threshold). Root cause identified: autonomous nightly channel only fires on *active* problems — no live KB staleness to trigger the block addition.
- conversation_enrichment_job.py shipped in PR #471 (batch_runtime.py, 50% cost reduction) but NOT wired into scheduled_jobs.py. The job runs nowhere.
- kb_hybrid_retrieval.py and kb_reranker.py shipped opt-in-off in PR #471. platform_flags.py (PR #476) now provides per-tenant DB toggle mechanism.
- platform_flags.py kill-switch semantics: DB=0 overrides env-var min. Size/count keys (e.g., voice_chat_max_tokens) could be accidentally zeroed; no guard exists.
- GH #413 REFERRAL_REWARD_ENABLED: Day 29+, 7 autonomous comments, 0 human responses. First appointment auto-complete is now live (PR #475). Window for referral-at-completion is opening.
- Three parking-lot items confirmed implemented: appointment_jobs.py, BotHealthPage.jsx, AttributionPage.jsx (all PR #475).
- AUTOPILOT_GH_TOKEN already tracked in ops/credential-rotation-schedule.md (next due 2026-10-02). Not a new gap.

---

## Idea 1: Step 9F — Channel Pivot to Human-Session Direct Edit

**Category:** workflow
**Effort:** XS (paste 28 lines into SKILL.md after Step 9E)
**Confidence:** HIGH

**What:** The exact Step 9F bash block from `subconscious/runs/2026-07-17-pm/winning-concept.md` should be inserted directly into `.claude/skills/nightly-commit-review/SKILL.md` in a human-interactive session, not delegated to the autonomous nightly channel.

**Why now:** Three consecutive nightly cycles have not added Step 9F. Root cause: Steps 9B-9E each triggered because nightly discovered a *live* problem (brain connector down, loop stalled, credential overdue). KB is currently healthy — no live trigger fires. The autonomous nightly channel cannot add Step 9F when nothing is broken. The human-session SKILL.md-edit channel is the correct mechanism. This is a carry-forward that requires channel pivot, not more waiting.

**Expected impact:** Every future nightly log gets "Step 9F: KB autopopulate last run: YYYY-MM-DD (N days ago)" — permanent observability. GH #403 gets automated comment when KB goes >7 days without a run. Prevents recurrence of the 72-day silent gap (2026-05-05 to 2026-07-09).

**Evidence refs:** winning-concept.md (runs 97, 98), grep Step 9F in SKILL.md returns 0, KB log.md last entry 2026-07-13.

---

## Idea 2: Wire conversation_enrichment_job.py into scheduled_jobs.py

**Category:** operational
**Effort:** S (2-file edit + test update, ~20 lines)
**Confidence:** HIGH

**What:** Add `conversation_enrichment_job` to `backend/services/automation/scheduled_jobs.py` so the Anthropic Batch API job runs on its intended cadence. The job lives at `backend/services/automation/scheduled/conversation_enrichment_job.py` (shipped PR #471) but has no scheduler entry — it runs nowhere in production.

**Why now:** batch_runtime.py delivers 50% cost reduction on offline AI jobs. conversation_enrichment_job.py is its first caller. A shipped feature that runs nowhere has zero value and zero cost savings. appointment_jobs.py (PR #475) proved the scheduling pattern is well-understood and already in the codebase. The parallel to auto_complete_past_appointments is exact: new scheduled/ file needs scheduled_jobs.py entry.

**Expected impact:** conversation enrichment runs on cadence → enriched leads feed qualification → downstream AI quality improves → batch API cost savings begin materializing. First measurable ROI from batch_runtime.py investment.

**Evidence refs:** scheduled_jobs.py lines 34+62 show auto_complete_past_appointments pattern, grep for conversation_enrichment in scheduled_jobs.py returns 0, batch_runtime.py in PR #471 commit.

**Risk note:** Need to verify the job's own rate controls and tenant iteration pattern before scheduling — must not fan out unboundedly to all tenants on first run.

---

## Idea 3: Enable kb_hybrid_retrieval via platform_flags Row for Keys Koffee

**Category:** customer_value
**Effort:** XS (1 SQL row in platform_settings table via Supabase MCP)
**Confidence:** MEDIUM

**What:** Insert a row into `platform_settings` enabling `kb_hybrid_enabled=1` for Keys Koffee's tenant_id. kb_hybrid_retrieval.py (PR #471) shipped opt-in-off; platform_flags.py (PR #476) provides the per-tenant DB toggle without any code deployment.

**Why now:** PR #476 (migration 175) landed 2026-07-19. The toggle mechanism now exists in production. kb_hybrid uses BM25 + pgvector reranking — meaningfully better retrieval for tenants with large, specific KBs. Keys Koffee is the pilot tenant for KB-first answers. The mechanism no longer requires a settings UI or GH issue-to-pr-loop.

**Expected impact:** Better retrieval quality for Keys Koffee widget responses. Validates the platform_flags toggle pattern in production before broader rollout. Zero code deployment risk — flip is DB-only and reversible.

**Blocker:** Supabase MCP is unavailable in headless/scheduled sessions. This idea requires a human-interactive session with Supabase MCP connected, OR a migration file (NNN_enable_kb_hybrid_keys_koffee.sql). As a subconscious recommendation, flag the path and let human execute.

**Evidence refs:** platform_flags.py (PR #476), kb_hybrid_retrieval.py (PR #471), Keys Koffee is primary KB tenant.

---

## Idea 4: platform_flags ALLOWED_TOGGLE_KEYS Guard

**Category:** code_health
**Effort:** S (1-file edit to platform_flags.py + test update, ~15 lines)
**Confidence:** MEDIUM

**What:** Add a `ALLOWED_TOGGLE_KEYS` frozenset to `backend/services/platform_flags.py`. When `resolve_int_setting` reads a `platform_settings` row, validate the key against the allowed list. If a non-toggle key (e.g., `voice_chat_max_tokens`, `ai_usage_limit`) appears in the table, raise a warning log or return None (failing open to env-var). This prevents accidental zeroing of size/count parameters via kill-switch semantics.

**Why now:** The nightly-commit-review 2026-07-19 logged this exact concern: "if a DB row is accidentally set to 0 for something like `voice_chat_max_tokens`, the Twilio/Claude call would receive `max_tokens=0` and fail." platform_flags.py is new (PR #476) — adding the guard now is cheap. In 6 months when 10+ keys exist in platform_settings, tracing an accidental zero will be painful.

**Expected impact:** Prevents a silent production failure mode where a misconfigured platform_settings row crashes voice calls or AI responses. Low effort, high insurance value.

**Evidence refs:** nightly-commit-review-2026-07-19.md lines 28-34 ("Minor concern: if a DB row is accidentally set to 0..."), platform_flags.py (PR #476).

---

## Idea 5: GH #413 Final Escalation — REFERRAL_REWARD_ENABLED Window Closing

**Category:** customer_value
**Effort:** XS (1 GitHub comment via mcp__github__add_issue_comment)
**Confidence:** MEDIUM

**What:** Post a final escalation comment on GH #413 framing REFERRAL_REWARD_ENABLED in terms of the new appointment-completion capability: first appointments are now auto-completing (PR #475 live). The review-request trigger fires on appointment completion. If REFERRAL_REWARD_ENABLED=1 is set before the first completed appointment, the referral reward is bundled with the first review request — highest leverage moment. If set after, the window is missed for those customers.

**Why now:** Day 29+, 7 comments, 0 human responses. The prior 7 comments focused on "referral program is ready" framing. PR #475 changes the context — appointment_jobs.py auto-completes confirmed+booked appointments past end_time+1h. First production completions are imminent. This is a new concrete trigger not present in prior comments.

**Expected impact:** Either action (human sets env var) or explicit "won't do" closes the loop. 29+ days of open uncertainty on a revenue feature warrants one final concrete escalation.

**Evidence refs:** GH #413 (OPEN Day 29+), scheduled_jobs.py lines 34+62 (auto_complete confirmed), PR #475 commit.

---

## Ranking for Debate

| Rank | Idea | Category | Effort | Confidence |
|------|------|----------|--------|------------|
| 1 | Step 9F channel pivot | workflow | XS | HIGH |
| 2 | conversation_enrichment scheduling | operational | S | HIGH |
| 3 | platform_flags ALLOWED_TOGGLE_KEYS guard | code_health | S | MEDIUM |
| 4 | kb_hybrid enable via platform_flags | customer_value | XS | MEDIUM |
| 5 | GH #413 final escalation | customer_value | XS | MEDIUM |

Top 3 for debate: Ideas 1, 2, 3.
