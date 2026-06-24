# Morning Digest — 2026-06-24

Generated: 2026-06-24 UTC | Caveman mode.

---

## Commits (last 24h) — 20+ landed

Heavy referral + vertical expansion day.

- `4a80f40` ops: nightly-commit-review 2026-06-24
- `6b0a7fb` migration 158: allow chatbot/agent_os in tenants_plan_check (APPLIED)
- `6b1e41c` Weekly digest: surface referral stats (signups/clicks) (#371)
- `f27fb0e` Weekly digest: surface referral stats — tenants already opt in
- `69e6789` Merge #370: referral signup notification email (backend-only)
- `1cc3338` Referral signup notification: email referrer on new signup via link
- `5b62a9b` brain: #369 merged; Vercel daily deploy quota exhausted — frontend blocked ~24h
- `3cb10d7` Merge #369: admin referral overview (completes admin analytics suite)
- `489eb0f` Admin referral overview: per-tenant clicks + referred-signups, ranked
- `f160480` brain: round-13 admin referral overview in progress
- `b15071c` Merge #368: referral signup attribution (channel measurable end-to-end)
- `027bfa8` brain: round-12 referral signup attribution
- `16bf8a7` Referral signup attribution: link ?ref= signups → referrer + referred_signups stat
- `0dc4839` brain: loop-status — buildable backlog exhausted post #367
- `852e8b0` Merge #367: vertical expansion 10→13 (roofing, home cleaning, veterinary)
- `c625825` Vertical expansion 10→13: KB + SEO + presets for 3 new verticals
- `f5fb9ae` Merge #366: G8 vertical expansion 7→10 (law firm, restaurant, fitness)
- `1f46788` G8 vertical expansion 7→10: KB + SEO + presets
- `e45ce27` brain: #365 merged + loop-status (high-value buildable backlog cleared)
- `d762443` Merge #365: fix funnel test harness to match internal-tenant exclusion

**Signal:** Referral tracking stack is now complete end-to-end (clicks → attribution → signup notification → admin overview → weekly digest stats). Vertical count: 13. Vercel deploy quota exhausted yesterday — frontend may have lagged.

---

## Issues — Open / Needs Action

### New (opened today)
- **#373** 🔴 BUG: Duplicate migration 158 — wizard_events fix likely **UNAPPLIED to prod**
  - `158_wizard_events_fix_step_range.sql` widens step CHECK (0–7) + adds `demo_referral` action
  - Without it: step-0 funnel events + demo_referral actions silently rejected by DB
  - Fix: rename → `160_wizard_events_fix_step_range.sql` → apply via Supabase MCP → update schema-log
  - Labels: bug, schema, medium-risk

### Persistent open
- **#68** memory-hygiene: frontmatter confidence + last_verified + access_count (ai-ready, P2)
- **#69** memory-hygiene: widget conversation memory tier — relevance scoring (ai-ready, P1)
- **#70** memory-hygiene: KB article provenance — source URL + stale warnings (ai-ready, P2)
- **#62** Zapier docs + KB articles (blocked by #58/#59/#60/#61)
- **#352** Yesterday's morning digest (can close)

### Stale migration issues (still open — may need close audit)
- Verify #292/#293 are fixed by commits `63cd035`/`c461cef` from yesterday — if confirmed, close them.

---

## Open PRs Needing Action

| # | Title | Age | Status |
|---|-------|-----|--------|
| #372 | Referral reward: $20 credit to referrer on first paid invoice | 1 day | DRAFT — awaiting migration 160 apply |
| #341 | KB drift sweep 2026-06-22 | 2 days | DRAFT — low risk, ready to merge |
| #328 | Billing: save-offer step before cancel (retention) | 6 days | DRAFT — needs review |
| #327 | AI Workforce: upgrade prompt on 402 | 6 days | DRAFT — 16 tests pass, ready |
| #325 | Checkout: kill Stripe Link emails + fix post-payment redirect | 6 days | DRAFT — 30 tests pass, ready |
| #286 | Agent OS fail/abstain alerts + email support form | 9 days | DRAFT — needs CI green |
| #86 | Fix 4 missing post-edit hook checks | 60 days | DRAFT — stale |
| #284 | python-jose ≥3.5.0 dep bump | 9 days | Open — safe to merge |
| #279/#281 | vitest 4.1.8→4.1.9 dep bumps (demo-platform) | 9 days | Open — auto-merge candidates |

**Priority merges:** #327 + #325 + #341 are all small, tested, low risk. Merge first. Then #372 once migration 160 is applied.

---

## Subconscious Recommendation (Run 64 — 2026-06-20-pm, 4 days stale)

**Winner:** Fix #292/#293 — wire `chatbot`/`agent_os` into `sms_rate_limiter`, `api_key_auth`, `billing_reconciliation` plan-name dicts.

**Current status:** Commits `63cd035` (rate-limit fix) + `c461cef` (plan_catalog wiring) from 2026-06-23 likely resolved this. Needs verification. If confirmed fixed → close #292/#293, subconscious mandate resolves.

**Still open (Bonus A from run 63/64):** #308 — webhook idempotency early-write drops payment events on Stripe retry. ~20 min fix. Human approval required. Sketch in `subconscious/runs/2026-06-20/winning-concept.md`.

**Subconscious last ran:** 2026-06-20-pm (4 days stale — expected daily).

---

## Automation Health

- **KB autopopulate:** Last log entry 2026-05-05 — **7 weeks stale**. Network sandbox + missing VOYAGE_API_KEY blocking cron. 4 articles in wiki/ pending kb_articles upsert.
- **Subconscious:** 4 days stale. Expected daily.
- **Embeddings:** Supabase MCP unauthorized — pgvector upserts failing. Widget KB retrieval degraded.
- **Vercel:** Daily deploy quota exhausted 2026-06-23 — frontend deploy lag possible. Check Vercel dashboard.

---

## Top 3 Priorities Today

1. **Fix migration #373 (URGENT)** — rename `158_wizard_events_fix_step_range.sql` → `160_wizard_events_fix_step_range.sql`, apply to prod via Supabase MCP, update schema-log. Step-0 funnel events and demo_referral actions are currently being silently dropped. Funnel analytics blind to these rows.

2. **Merge ready PRs: #327 + #325 + #341** — all tested, all low risk, all been sitting 6+ days. #327 (402 upgrade screen) and #325 (checkout UX fixes) directly improve paid conversion. Merge today.

3. **Apply migration 160 → merge #372 (referral rewards)** — once migration conflict resolved (priority 1), migration 160 for `referral_rewards` table can be applied and PR #372 merged. Completes the referral monetization loop.

**Bonus:** Verify #292/#293 closed by yesterday's commits. Fix #308 (webhook idempotency) — 20 min, low risk, high impact on dunning-locked tenants.

---

*Next digest: 2026-06-25 morning.*
