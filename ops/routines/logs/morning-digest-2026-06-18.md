# Morning Digest — 2026-06-18

Generated: 2026-06-18 UTC | Caveman mode.

---

## 🔴 CRITICAL — ACT NOW

**#331: 29 commits NOT pushed to any remote branch — container expiry risk**
- ~2 weeks of work lives only in this container's git objects
- Includes: billing repricing ($19.99 chatbot / $99.99 agent_os), migration 154, instant KB from URL, AI Workforce gating, lead alerts hardening, Front Desk Health card, Conversation Insights, TermsOfService rewrite, Stripe Link disable, trial removal
- **If container expires → work gone**
- Fix: `git checkout -b main-pending d7c574b && git push -u origin main-pending`

---

## Commits — Last 24h (29 commits)

- `d7c574b` Billing: add save-offer step before cancel (retention, compliant)
- `8e523f1` AI Workforce: show upgrade prompt on 402 instead of raw error
- `20108e7` Messaging: punch up welcome email branding + align ToS to current plans
- `9e139a5` Checkout: land non-wizard customers on /dashboard, not dead /billing/success
- `45a228a` Checkout: disable Stripe Link (stop the 'Welcome to Link' wallet emails)
- `af9a90b` docs: auto-log bug fix from 8af5e94
- `8af5e94` Fix em-dash in Tidio FAQ copy
- `0f0b12a` Marketing pages: correct stale pricing/trial copy to current model
- `ecb5c34` Support email: unify to support@agentnexlify.com
- `61947b9` Gate AI Workforce (Agent OS) to the agent_os plan
- `6bb8f10` Welcome email: remove em dashes
- `13917a8` Update checkout test: assert immediate charge (no trial)
- `273c49b` Billing: charge immediately on signup — remove 7-day checkout trial
- `727bf2e` Pricing: AI Front Desk CTA reads 'Get Started' (match AI Workforce) (#321)
- `f6416a9` subconscious: run 2026-06-17-pm — Fix GH #308 webhook idempotency early-write
- `1f642f7` Free-to-paid usage upgrade nudge (#320)
- `e9474cb` Add Front Desk Health overview card to dashboard home (#319)
- `6894d53` Add Outbound Outreach agent to AI Workforce (#318)
- `a7ece95` Harden instant new-lead owner alerts (email + SMS, idempotent) (#317)
- `2e00b5f` Conversation Insights: monthly auto-run + dashboard surface (#316)
- `93d9b85` Stored conversation sentiment + intent (#315)
- `79ff623` Instant KB from website URL in onboarding (#313)
- `8de99ec` Make /demo a hands-on interactive product sample (#314)
- `cf297b2` Add Conversation Insights agent to AI Workforce (#312)
- `ec22250` Rename demo CTAs to live-demo framing (#311)
- `b2afaf2` docs: auto-log bug fix from 9f76829
- `9f76829` Fix AgentShield CI (Linux runner) + finish brand-tagline pluralization (#310)
- `0104c14` ops: morning-digest 2026-06-17

---

## Issues — Open / Actionable

| # | Title | Status | Priority |
|---|-------|--------|----------|
| #331 | 29 pending commits not on any remote branch — container expiry risk | OPEN | 🔴 CRITICAL |
| #330 | Human legal review: TermsOfService section 4 rewritten | OPEN | 🟡 HIGH |
| #329 | Apply migration 154 (conversation sentiment + intent) to production | OPEN | 🟡 HIGH |
| #308 | MEDIUM: Webhook idempotency early-write drops events on handler failure | OPEN | 🟡 HIGH |
| #293 | MEDIUM: orchestrator + billing_reconciliation use stale plan names | OPEN | 🟡 HIGH |
| #292 | MEDIUM: sms_rate_limiter + api_key_auth missing new plan names (chatbot/agent_os) | OPEN | 🟡 HIGH |
| #266 | security: finish integrations-secret encryption — backfill + sunset | OPEN | 🟠 MED |
| #265 | deps: re-raise the fastapi <0.136 cap once starlette is bumped | OPEN | 🟠 MED |
| #263 | Schema Sync [CRITICAL]: 24 pending migrations | OPEN | 🟠 MED |
| #217 | Stripe Connect: self-serve own-payments (BLOCKED on billing-arch) | OPEN | 🔵 BLOCKED |
| #193 | Moratorium active: 13 pending items, oldest 44 days | OPEN | ℹ️ TRACKING |

---

## Open PRs Needing Action

| # | Title | State | Notes |
|---|-------|-------|-------|
| #328 | Billing: save-offer step before cancel | Draft | Ready for review |
| #327 | AI Workforce: upgrade prompt on 402 | Draft | Ready for review |
| #325 | Checkout fixes: kill Stripe Link + land paid users on dashboard | Draft | Ready for review |
| #286 | feat(os+support): Agent OS fail/abstain alerts + email-routed support | Draft | Older, needs review |
| #284 | chore: update python-jose requirement | Open | Dependabot — review |
| #283 | chore: bump uvicorn to 0.49.0 | Open | Dependabot — review |
| #282 | chore: update stripe requirement | Open | Dependabot — review |
| #281 | chore: bump @vitest/coverage-v8 | Open | Dependabot — minor |
| #280 | chore: bump react 18→19 in demo-platform | Open | Dependabot — risky, test first |
| #279 | chore: bump vitest in demo-platform | Open | Dependabot — minor |

---

## Subconscious — Latest Recommendation

**Run:** 2026-06-17-pm (run #59) | **Winner:** Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events

**TL;DR:** `idempotency.py` writes the row BEFORE handler completes. On handler throw → row stuck as `processing` → Stripe retry hits `is_new=False` → returns 200 → event permanently dropped → tenants stay dunning-locked after card fix. Fix: wrap handler in try/except, delete idempotency row on exception before re-raise. 3 files, ~15 lines. Nightly review path recommended for today.

**Bonus A (after #308):** Wire `chatbot`/`agent_os` into `sms_rate_limiter.py`, `api_key_auth.py`, `orchestrator.py`, `billing_reconciliation.py` — requires SMS limit product decision (proposed: chatbot=200/day, agent_os=500/day).

**Bonus B (after Bonus A):** Add plan-name guard (check 7) to `check_project_invariants.py` — AUTONOMOUS-EXECUTABLE.

---

## KB — Last Update

KB log last cron: 2026-05-05 (stale — no successful update since). Likely blocked by network sandbox + missing Voyage API key in cron env. Needs manual reindex once env vars restored.

---

## Top 3 Priorities Today

### 1. 🔴 Push 29 commits to a named remote branch (BEFORE CONTAINER EXPIRES)
```bash
git checkout -b main-pending d7c574b
git push -u origin main-pending
```
Everything else is moot if these commits disappear.

### 2. 🟡 Fix GH #308 — Webhook idempotency early-write (payment revenue bug)
Nightly review has a complete sketch. 3 files, ~15 lines. Tenants are dunning-locked after card fix until this lands. Subconscious confidence: HIGH. Nightly review can implement today if moratorium override confirmed.

### 3. 🟡 Apply migration 154 to production + wire plan names into 4 files (#329, #292, #293)
Migration 154 (conversation sentiment + intent) is live in the codebase but not in prod DB. Also: new plan names (`chatbot`/`agent_os`) are missing from `sms_rate_limiter.py`, `api_key_auth.py`, `orchestrator.py`, `billing_reconciliation.py` — new paid tenants get broken SMS/Zapier/email.

---

## Watchlist

- **Legal review #330** — TermsOfService section 4 rewritten (payment terms). Needs human eyes before next billing cycle.
- **Dependabot react 18→19 (#280)** — risky, test demo-platform before merging.
- **Moratorium (#193)** — 13 items pending. Oldest 44 days. Container expiry makes moratorium moot if commits aren't pushed first.

---

*Auto-generated by morning-digest routine. Next: /evening or nightly-commit-review.*
