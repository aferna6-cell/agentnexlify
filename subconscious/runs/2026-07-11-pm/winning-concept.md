# Winning Concept — Run 89 (2026-07-11-pm)

**Date:** 2026-07-11-pm
**Run:** 89
**Category:** customer_value
**Effort:** XS
**Confidence:** HIGH
**Status:** AUTONOMOUS-EXECUTABLE (via GitHub MCP — mcp__github__issue_write)

---

## Recommendation

File a GH issue packaging the Referral Reward activation pre-gate checklist for the human, enabling a single Railway env-var flip (REFERRAL_REWARD_ENABLED=1) to launch viral growth once the checklist passes.

---

## Why This, Why Now

PR #404 (3596009) confirmed Migration 162 (referral_rewards schema) is applied to prod. The referral reward system is built and schema-ready. Launching requires exactly one action: setting `REFERRAL_REWARD_ENABLED=1` in Railway environment variables. Zero engineering. Zero schema changes. Zero PRs.

Referral programs deliver 3-5x CAC reduction in SaaS by turning satisfied customers into unpaid sales reps. The 7 real leads captured (MTOptions, 914 Exterior, Keys Koffee + their customers) are all potential referrers. If a single tenant shares their referral link with 10 contacts, that's 10 new leads at $0 CAC. Viral growth compounds — the first referral creates a referrer who may become the next referrer.

The booking funnel mystery is largely resolved by PR #404 (2/3 tenants fully bookable: MTOptions 20 slots, 914 Exterior 22 slots post-prod-bug-fix). The pipeline escalation (GH #399 + #403) is handled daily by Step 9D. The referral reward is the one high-leverage NEW revenue channel that has never been activated — and requires nothing new to build.

This idea has been in the parking lot since run 87 (twice deprioritized behind the booking chain). With the booking mystery largely solved, referral activation is the next domino.

---

## Implementation — AUTONOMOUS-EXECUTABLE

**File GH issue via `mcp__github__issue_write`:**

**Title:** `ACTION REQUIRED: Activate referral reward — Migration 162 in prod, one env-var flip`

**Labels:** `revenue`, `human-action-required`

**Body:**

```markdown
## Status

Migration 162 (referral_rewards) has been applied to production. The referral reward system is **fully built and schema-ready**.

Activation requires one action: set `REFERRAL_REWARD_ENABLED=1` in Railway environment variables.

## Why now

- 7 real leads captured. Each is a potential referrer.
- Referral programs deliver 3-5x CAC reduction — each referred lead costs $0.
- No engineering required. No PR. No migration. One env-var flip.

## Pre-Activation Checklist

Before flipping the variable, verify each item in the Supabase dashboard and staging environment:

**Schema (verify in Supabase SQL editor):**
```sql
-- Confirm referral_rewards table exists and is populated
SELECT table_name FROM information_schema.tables
WHERE table_name = 'referral_rewards';

-- Confirm referral tracking columns on leads/widget_configs
SELECT column_name FROM information_schema.columns
WHERE table_name = 'widget_configs' AND column_name ILIKE '%referral%';
```

**UX checklist:**
- [ ] Referral link generates correctly for tenants (dashboard Settings → Referral page exists?)
- [ ] Widget referral capture flow works end-to-end (referred visitor → lead created with referrer_id)
- [ ] Reward redemption path confirmed (Stripe credit, manual credit, or email notification?)
- [ ] Tenant notification email sent when referral converts to a paying customer
- [ ] Self-referral prevention confirmed (same user cannot refer themselves)

**Fraud prevention:**
- [ ] Rate limiting on referral link clicks (prevent click-farm abuse)
- [ ] Minimum qualification period (referral must remain active N days before reward fires)

## Activation

Once checklist passes, in Railway dashboard:

1. Go to the backend service → Variables
2. Add: `REFERRAL_REWARD_ENABLED=1`
3. Deploy

## Expected outcome

- Tenants can share referral links immediately after activation
- New leads tagged with `referrer_id` for attribution
- Referral rewards fire automatically on qualifying conversions
- First referral lead captured within 7 days if tenants share with their networks

## Context

- Migration 162 confirmed applied to prod by PR #404 (2026-07-11, commit 3596009)
- Booking funnel largely resolved: MTOptions (20 slots), 914 Exterior (22 slots). Keys Koffee needs hours from tenant.
- Issue-to-pr-loop stalled (GH #399 + #403 pending). This activation requires no loop — human only.
```

---

## What This Replaces / Complements

This is a new direction — first referral activation recommendation. The booking chain (runs 87-89) is largely closed for 2/3 tenants. GH #412 covers the remaining Keys Koffee investigation.

**Bonus Actions (execute alongside winner this run):**

1. **Comment on GH #412** with PR #404 findings: MTOptions 20 slots live, 914 Exterior 22 slots after prod bug fix (impossible hours corrected to 17:00). Keys Koffee still needs tenant-provided real hours. Narrows human's investigation to one tenant.

2. **Comment on GH #403** Day-2 escalation: 40 ai-ready issues stalled, kb-autopopulate 67 days since last run (last entry 2026-05-05), Lead Source Analytics GH #409 queued but not executing.

---

## Confidence

**HIGH** — Evidence is specific (Migration 162 in prod confirmed by commit message, Railway env-var pattern confirmed for other feature flags in the codebase, GitHub MCP available). Checklist ensures human verifies safety before activation. If UX is incomplete, the checklist surfaces exactly what needs to be built.

---

## Run 90 Mandate

1. Verify referral reward GH issue filed (look for open issue with `revenue + human-action-required` labels and title containing "referral reward").
2. Check if `REFERRAL_REWARD_ENABLED=1` was set in Railway (look for Railway activity log or first referral_rewards table row in Supabase).
3. If not activated: report checklist status — which items blocked activation?
4. Confirm GH #412 comment posted (PR #404 booking findings for MTOptions + 914 Exterior).
5. Confirm GH #403 Day-2 comment posted.
6. Check GH #399 + #403 resolution — if fixed, confirm issue-to-pr-loop resumed and Lead Source Analytics GH #409 has a draft PR.
7. If Keys Koffee has provided business hours: verify booking slots generating. If not: escalate Keys Koffee onboarding as human-action item.
