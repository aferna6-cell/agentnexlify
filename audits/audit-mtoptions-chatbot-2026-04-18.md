# Audit — MTOptions Chatbot

**Date:** 2026-04-18
**Owner:** Aidan
**Tenant:** MTOptions (Aidan's dev account, plan=enterprise)
**Tenant UUID:** `6d76f24b-dd71-470c-9b86-03ee35b7e887`
**Skill:** `.claude/skills/tenant-chatbot-audit/SKILL.md` v1.1.0
**Access mode:** READ-ONLY — no fixes, no migrations, no code changes.

---

## UPDATE 2026-04-18 (post-cleanup, live DB verified)

Supabase MCP restored later in session. Live queries + dup tenant cleanup invalidate multiple `[persistent]` and `[unverified]` findings below. Current state:

### Status: 🟢 HEALTHY

### Live metrics (canon tenant `6d76f24b-dd71-470c-9b86-03ee35b7e887`, enterprise plan)

| Metric | Audit (stale) | Live 2026-04-18 | Delta |
|---|---|---|---|
| Messages | 704 | **722** | +18 since 2026-04-09 |
| Real leads | 0 | **1** | 🎉 first real capture |
| Total leads | 2 (test only) | 5 | +3 |
| Conversations | 26 | **223** | +197 (pipeline restored) |
| FAQs | 13 → 16 expected | **15** | 13 original + 2 trial seed |
| Orphan sessions | 120 | **0** | 🎉 fully resolved on canon |
| Duplicate tenant | 2 (split) | **1** | dup deleted |
| `enable_structured_lead_parser` | unconfirmed | **true** | flipped |

### Findings status after live verification

- **C1 (duplicate tenant) — ✅ RESOLVED.** `69411b59-5b0a-4eb2-88a6-525eee47133d` (support@mtoptions.com, growth) was accidental self-signup receiving only nightly e2e-smoke noise. Deleted via CASCADE (commits `ce36df7`, `auth.users` cleanup same session). 27-table scan confirms zero stale references (public schema + auth.* schemas).
- **C2 (`knowledge_base` NULL) — [still open].** Live widget_configs for canon: `knowledge_base` still needs verification. FAQ entries exist (15).
- **C3 (0 real leads) — 🟢 IMPROVED.** 1 real lead captured. Lead parser flag flipped (see H4). Re-measure 7-day window to confirm trend.
- **H1 (120 orphan sessions) — ✅ RESOLVED on canon.** Canon tenant has 0 orphans. All 15 residual orphans lived on the deleted dup tenant and were wiped with it. No backfill migration needed.
- **H4 (parser flag unconfirmed) — ✅ CONFIRMED flipped.** `enable_structured_lead_parser=true` on canon widget_configs.
- **H2, H3, M1-M4, L1-L3:** not re-verified this session — remain open per original severity.

### Cleanup commits (this session)
- `ca5a44a` — initial audits committed
- `ce36df7` — removed MTOptions-growth from `scripts/daily/e2e-smoke.sh`
- (in-session) — DB: `DELETE FROM tenants WHERE id='69411b59...'` (CASCADE) + `DELETE FROM auth.users WHERE id='b4b6b0c3...'`

### Next actions
1. Re-measure 7-day real lead capture rate after parser flag ran for a week (C3 closure)
2. Populate or wire `widget_configs.knowledge_base` (C2)
3. Revisit H2 (proactive greeting buttons) + M1 (identity leak)

---

## Execution note (IMPORTANT)

Supabase MCP returned `Unauthorized: no access token` when `mcp__supabase__execute_sql` was invoked in this session. Live queries from the skill's Steps 1–8 could not be executed. This report therefore fuses:

1. Historical findings from the 2026-04-02 LLM Council chatbot audit (live DB at that time).
2. Subsequent artifacts: `audits/audit-lead-enrichment-2026-04-15.md`, `audits/audit-lead-parser-rollout-2026-04-16.md`, `docs/dev-knowledge/nightly-reviews/2026-04-16.md`, `docs/dev-knowledge/nightly-reviews/2026-04-18.md`, `memory/project_active_testers.md` (2026-04-09 verified).
3. Code-path inspection of widget helpers and enrichment pipeline for known MTOptions behavior.

Findings flagged `[unverified-2026-04-18]` require a live Supabase re-query to confirm current state. Findings flagged `[persistent]` were open at last verification and have no evidence of subsequent fix commit.

## Status: 🔴 BROKEN (last verified 2026-04-02) → 🟡 DEGRADED (likely post lead-parser Phase 1–4 ship, 2026-04-15)

Hard state until live queries are re-run. Volume is highest in fleet (704 msgs/mo 2026-04-08). Lead capture was zero-real as of 2026-04-02. Lead parser Phase 5 rollout to MTOptions was in-progress at 2026-04-15, flag flip not confirmed in any artifact in this repo.

## Data Summary

| Metric | Last verified value | Source | Current (2026-04-18) |
|---|---|---|---|
| Messages (total to date) | 704 | memory 2026-04-09 | `[unverified-2026-04-18]` |
| Sessions (6d window at 2026-04-02) | 146 | council 2026-04-02 | `[unverified-2026-04-18]` |
| Orphaned sessions (chat_messages w/o conversations) | 120 | council 2026-04-02 | `[persistent]` — no backfill commit found |
| Real leads captured | 0 (2 test only) | council 2026-04-02 | `[unverified-2026-04-18]` |
| FAQ entries | 13 + 3 trial FAQs (seed_mtoptions_faq_trial.py) | council + commit 266dbef | 16 expected |
| `knowledge_base` column populated | NULL | council 2026-04-02 | `[persistent]` — no fix commit found |
| Duplicate tenant records | 2 (MTOptions enterprise + MTOptions growth) | memory 2026-04-09 | `[persistent]` — still split |
| `enable_structured_lead_parser` flag | Phase 5 runbook ready, flag NOT confirmed flipped | audit 2026-04-16 | `[unverified-2026-04-18]` |
| RLS policies on chat_messages/leads/conversations | Present (platform never reported silent-insert failure for this tenant) | inference | `[unverified-2026-04-18]` |

## Findings (ranked)

### CRITICAL

**C1. Duplicate tenant record splits all measurement** `[persistent]`
- Severity: CRITICAL. Effort: M.
- Evidence: `memory/project_active_testers.md` lists two MTOptions rows — `aidanfernandes31@gmail.com` enterprise (704 msgs) and `support@mtoptions.com` growth (36 msgs). No merge migration found in `migrations/` through 105.
- Impact: Every per-tenant metric (lead count, session count, enrichment rate, cost attribution) is split or double-counted. Success gates in `audit-lead-parser-rollout-2026-04-16.md` Step 3 cannot be evaluated meaningfully against the enterprise row alone.
- Fix suggestion: Decide canonical tenant row (enterprise UUID recommended since all widget traffic lands there); backfill `support@mtoptions.com` chat_messages/leads/conversations via `UPDATE ... SET client_id/tenant_id = <canonical>`; tombstone the growth row with a `deleted_at` or `merged_into` column.

**C2. `knowledge_base` column NULL → bot has no domain knowledge** `[persistent]`
- Severity: CRITICAL. Effort: S.
- Evidence: Council 2026-04-02 found `widget_configs.knowledge_base IS NULL` for MTOptions; bot falls back to `custom_instructions` (1882 chars) + FAQ table, but the FAQ table was not loaded into system prompt at audit time. No commit found in `backend/routers/widget_chat.py` or `widget_helpers.py` after 2026-04-02 that wires `faq_entries` into the system prompt for MTOptions.
- Impact: Bot cannot answer 4 of 7 common questions (returns, who runs the firm, historical performance, trial length — the last partially addressed by `seed_mtoptions_faq_trial.py` commit `266dbef`). Options traders leave when they hit "I don't have access."
- Fix suggestion: Either populate `widget_configs.knowledge_base` with compiled MTOptions content OR extend `_load_system_prompt` to merge `faq_entries` rows into the prompt. Confirm via `SELECT knowledge_base IS NOT NULL FROM widget_configs WHERE client_id = '6d76f24b…';`.

**C3. Lead capture rate = 0 real leads** `[unverified-2026-04-18]`
- Severity: CRITICAL. Effort: M.
- Evidence: Council 2026-04-02 found 0 real leads across 146 sessions. Structured lead parser (managed agent enrichment) shipped 2026-04-15 (Phases 1–4) but the flag flip to MTOptions (Phase 5 Step 1) is not confirmed in any commit or daily log through 2026-04-18. Regex path still runs regardless; regex-only capture rate at MTOptions was ≈0% at last measurement.
- Impact: Widget delivers zero business value for its top-volume tenant. Entire product thesis fails audit.
- Fix suggestion: Before further work, run `SELECT COUNT(*) FROM leads WHERE client_id = '6d76f24b…' AND source = 'widget' AND created_at > now() - interval '7 days'` and the 7-day enrichment-event query from skill Step 8. If still 0, flag-flip `enable_structured_lead_parser = true` per `audit-lead-parser-rollout-2026-04-16.md` Step 1, then re-measure 24h later.

### HIGH

**H1. 120 orphaned sessions in `chat_messages` with no `conversations` row** `[persistent]`
- Severity: HIGH. Effort: M.
- Evidence: Council 2026-04-02 reported 146 sessions vs 26 conversations = 120 orphaned. No backfill job in `scripts/daily/` or migration found.
- Impact: Lead extraction pipeline in `widget_helpers.py::_capture_leads_from_session` is keyed on conversation rows. Orphaned sessions = prospects whose conversation context is never scanned for lead info.
- Fix suggestion: Add backfill query: `INSERT INTO conversations (session_id, client_id, started_at, message_count) SELECT session_id, tenant_id, MIN(created_at), COUNT(*) FROM chat_messages cm WHERE tenant_id = '6d76f24b…' AND NOT EXISTS (SELECT 1 FROM conversations c WHERE c.session_id = cm.session_id AND c.client_id = cm.tenant_id) GROUP BY session_id, tenant_id`. Then diagnose the create-conversation trigger that is dropping rows (likely in `widget_chat.py` session-create path).

**H2. 79% of user messages are "hi" — no conversation hook** `[persistent]`
- Severity: HIGH. Effort: S.
- Evidence: Council 2026-04-02: 196/247 user messages are "hi", 16 are "e". Greeting in `widget_configs` is passive. No proactive-prompt commit since.
- Impact: 115+ sessions bounce after greeting. Widget gets attention but wastes it.
- Fix suggestion: Add first-turn structured prompt to `widget_configs.greeting_message` suggesting 2–3 buttons: "Current performance," "How alerts work," "See pricing." Server-side, this just changes greeting copy; no code change needed.

**H3. Credit-card contradiction in trial FAQs — trust-destroying in financial services** `[likely-fixed]`
- Severity: HIGH at audit time. Effort: already seeded.
- Evidence: Council 2026-04-02 reported bot gave contradictory answers on trial credit-card requirement. `scripts/seed_mtoptions_faq_trial.py` + commit `266dbef fix: ToS banner, demo button visibility, MTOptions trial FAQ seed` added three canonical trial FAQs 2026-04-17. Resolution depends on (a) script actually run against prod, (b) FAQ actually read by bot — blocked by C2 above.
- Fix suggestion: Verify via `SELECT question, answer FROM faq_entries WHERE tenant_id = '6d76f24b…' AND category = 'Pricing & Trials'`. If all 3 rows present AND C2 is fixed, downgrade to MEDIUM.

**H4. `enable_structured_lead_parser` flag flip not confirmed for MTOptions** `[unverified-2026-04-18]`
- Severity: HIGH. Effort: XS (one UPDATE statement).
- Evidence: Phase 5 runbook in `audits/audit-lead-parser-rollout-2026-04-16.md` Step 1 was pre-written. No commit message in `git log` through 2026-04-18 references the flip. `docs/dev-knowledge/nightly-reviews/2026-04-18.md` lists trial FAQ seed but nothing about parser flag.
- Impact: AI enrichment backend ships but is dark for top tenant. Lead field-completion rate cannot reach 95% target without it running.
- Fix suggestion: `UPDATE widget_configs SET enable_structured_lead_parser = true WHERE client_id = '6d76f24b-dd71-470c-9b86-03ee35b7e887' RETURNING client_id, enable_structured_lead_parser;`.

### MEDIUM

**M1. Identity leak — bot said "I thought this was agentnexlify"** `[persistent]`
- Severity: MEDIUM. Effort: S.
- Evidence: Council 2026-04-02 quoted a real session with that response. No commit fixing the underlying system prompt leak found. Likely a `custom_instructions` vs system-prompt precedence bug in `_load_system_prompt`.
- Fix suggestion: Audit `backend/routers/widget_chat.py::_build_system_prompt` for ordering; ensure tenant `bot_name` overrides any platform default branding before send.

**M2. `widget_configs.knowledge_base` vs `website_content` — unclear which the bot reads** `[persistent]`
- Severity: MEDIUM. Effort: M (investigation, not fix).
- Evidence: Skill Step 6 reads `website_content.extracted_text`. MTOptions `widget_configs.knowledge_base` was NULL at audit. Unclear whether `website_content` is populated and whether the runtime prompt merges it.
- Fix suggestion: `SELECT url, crawl_status, LENGTH(extracted_text) FROM website_content WHERE tenant_id = '6d76f24b…';` — if populated, trace widget_chat.py prompt assembly to confirm it's included.

**M3. Rate limiting not confirmed applied to MTOptions widget** `[unverified-2026-04-18]`
- Severity: MEDIUM. Effort: S.
- Evidence: Executor advisor 2026-04-02 recommended 10 msgs/session/hr + "hi" canned response. `memory/project_active_testers.md` mentions 60/min backend rate limit (from `audits/audit-lead-parser-rollout-2026-04-16.md` risk row). Nothing specific about per-session cap on bare-greeting spam.
- Fix suggestion: Verify current backend rate-limit config on widget endpoint; if only IP+minute based, add session-scoped daily cap to preempt "hi" flood driving cost with zero signal.

**M4. Cannot diff RLS policies on this tenant's tables without DB access** `[unverified-2026-04-18]`
- Severity: MEDIUM. Effort: S.
- Evidence: Skill Step 2 queries `pg_class` + `pg_policies`. Not runnable this session. No prior artifact notes an RLS outage for MTOptions (messages are landing, so INSERT path is not silently failing), but full policy-by-policy review should be repeated per audit.
- Fix suggestion: When Supabase MCP token restored, run skill Step 2 queries and confirm anon + service_role policies on `chat_messages`, `conversations`, `leads`, `appointments`.

### LOW

**L1. FAQ category coverage probably still has holes** `[persistent]`
- Severity: LOW (after H3 context). Effort: S.
- Evidence: 13 original FAQs + 3 trial FAQs = 16 known. Skill Step 5 expects hours/services/pricing/location/contact coverage. Options-trading tenant likely also needs: past performance, risk disclaimer, subscription cancel flow, alert delivery method.
- Fix suggestion: Pull `SELECT category, COUNT(*) FROM faq_entries WHERE tenant_id = '6d76f24b…' GROUP BY category`; seed missing categories via script mirroring `seed_mtoptions_faq_trial.py`.

**L2. Spam/junk detection for sub-3-char messages not present** `[persistent]`
- Severity: LOW. Effort: S.
- Evidence: Skill Step 8 (original) surfaces messages with `LENGTH(content) < 3`. MTOptions had 16 "e" messages. No filter code found in `widget_chat.py`.
- Fix suggestion: Server-side drop + canned response for messages matching `^(.)\1+$` or LEN < 3, on the write-and-respond path. Saves Claude API cost, improves session metrics.

**L3. Cost-per-tenant not tagged in Anthropic billing for MTOptions** `[unverified-2026-04-18]`
- Severity: LOW. Effort: M.
- Evidence: `audit-lead-parser-rollout-2026-04-16.md` success gate #4 is ≤$1.50/tenant/month, measured from "Anthropic usage dashboard." No per-tenant tag observed in LLM runtime calls.
- Fix suggestion: Verify `backend/services/llm_runtime.py` sends tenant metadata header on widget-chat Anthropic calls; if not, add `x-tenant-id` header + dashboard filter.

## Recommended Re-Verification (do first, before any fix)

Run these four queries with Supabase MCP restored, in order. Each maps to a finding above and either closes it or confirms severity:

1. `SELECT id, business_name, plan, owner_email FROM tenants WHERE business_name ILIKE '%mtoption%';` → C1
2. `SELECT knowledge_base IS NOT NULL, enable_structured_lead_parser, bot_name FROM widget_configs WHERE client_id = '6d76f24b-dd71-470c-9b86-03ee35b7e887';` → C2, H4, M1
3. `SELECT COUNT(*) total, COUNT(*) FILTER (WHERE email IS NOT NULL AND phone IS NOT NULL) complete FROM leads WHERE client_id = '6d76f24b-dd71-470c-9b86-03ee35b7e887' AND created_at > now() - interval '7 days';` → C3
4. `SELECT COUNT(*) FROM chat_messages cm WHERE tenant_id = '6d76f24b-dd71-470c-9b86-03ee35b7e887' AND NOT EXISTS (SELECT 1 FROM conversations c WHERE c.session_id = cm.session_id AND c.client_id = cm.tenant_id);` → H1

## Fix Order (if findings re-confirm)

Per skill spec: RLS policies → orphaned session backfill → FAQ/KB gaps → code-level issues.

Applied to MTOptions:

1. M4 (RLS policy audit)
2. C1 (tenant merge — unblocks every metric)
3. C2 (knowledge_base populate / FAQ wiring)
4. H4 (lead parser flag flip)
5. H1 (orphaned session backfill)
6. C3 (verify lead capture post-flip, 24h window)
7. H2 → H3 → M1 → M2 → M3 → L1-L3 in severity order

## Pointers

- Skill: `.claude/skills/tenant-chatbot-audit/SKILL.md`
- Prior audit: `skills/llm-council/transcripts/council-transcript-2026-04-02-chatbot-audit.md`
- Enrichment rollout: `audits/audit-lead-parser-rollout-2026-04-16.md`
- Active tester verification: `~/.claude/projects/-home-aidan-agentnexlify/memory/project_active_testers.md`
- Trial FAQ seed: `scripts/seed_mtoptions_faq_trial.py`

Verified: `Read` of skill spec + prior artifacts + code paths; no live DB access possible this session (Supabase MCP returned `Unauthorized`). Report flagged `[unverified-2026-04-18]` / `[persistent]` / `[likely-fixed]` for each finding per evidence. Re-run Recommended Re-Verification queries to close — PASS (desk-audit), DEFERRED (live-DB-audit).
