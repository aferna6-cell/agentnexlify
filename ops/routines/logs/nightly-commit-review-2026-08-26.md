# Nightly Commit Review — 2026-08-26

**Window:** last 24 hours  
**Commits reviewed:** 4  
**Issues found:** 1 MEDIUM (no LOW auto-fixes needed)

---

## Commits Triaged

### 1. `1d964f5` — ops: morning-digest 2026-08-25
**Risk:** LOW  
**Assessment:** Log file only. No code changes.

### 2. `5bc0288` — ops: correct Step 9J result in nightly-commit-review-2026-08-25
**Risk:** LOW  
**Assessment:** Log file correction. No code changes.

### 3. `5cdc0c1` — ops: nightly-commit-review 2026-08-25
**Risk:** LOW  
**Assessment:** Log file only. No code changes.

### 4. `10acf83` — Revenue: all 10 profit-plan ideas (#686)
**Risk:** HIGH  
**Assessment:** Owner-directed session (Claude Fable 5). Large billing/payments/schema commit.

**Files touched:**
- `backend/routers/auth_billing.py` — annual billing interval support
- `backend/routers/billing.py` — voice addon webhook handlers, AMOUNT_TO_PLAN expansion
- `backend/routers/billing_addons.py` — NEW: voice addon checkout endpoint
- `backend/routers/partners.py` — NEW: agency inquiry endpoint
- `backend/services/stripe_service.py` — annual price IDs, managed tier, voice addon price
- `backend/services/churn_watch.py` — churn call list with activity queries
- `migrations/194_voice_addon.sql` — `tenants.voice_addon_active` column (applied to prod)
- Frontend: BillingPage, Partners page

**What's correct:**
- Annual billing interval validated at all three checkout endpoints
- Voice addon isolated from plan webhook handlers via `metadata.addon == 'voice'`
- All new revenue surfaces env-gated dark (503 returned until real Stripe price IDs set)
- `client_id` correctly used on leads table in churn_watch.py (Critical Rule #1 respected)
- `tenant_id` correctly used on chat_messages table
- Partners endpoint: honeypot + rate-limit + html.escape on all user content
- Migration 194 additive-only (IF NOT EXISTS guard)
- Test suite passed per commit: 294 backend tests, 263/263 frontend

**Issue found — MEDIUM risk:**
Voice addon upgrade-path gap: a chatbot tenant who purchases the voice add-on (+$49.99/mo) and later upgrades their base plan to `agent_os` ($99.99/mo, which already includes voice) will be double-billed. The `billing_addons.py` guard prevents buying the addon on `agent_os`, but `billing_change_plan` in `auth_billing.py` has no logic to detect or cancel an active voice addon subscription on upgrade. GitHub issue created: see below.

**No LOW-risk bugs auto-fixed** (sole issue is in payments/billing path — requires human approval per CLAUDE.md).

---

## Actions Taken

- Created GitHub issue #687 for voice addon double-billing gap (MEDIUM risk, label: `nightly-review`, `risk:medium`, `billing`) — https://github.com/aferna6-cell/agentnexlify/issues/687
- No code changes (all findings in auth/payments/billing — off-limits without human approval)

---

## CRITICAL RULE CHECK (per CLAUDE.md)

| Rule | Status |
|------|--------|
| `client_id` not `tenant_id` on leads | ✓ Correct in churn_watch.py |
| `status` not `lead_stage` | ✓ Not touched |
| No `from __future__ import annotations` | ✓ billing_addons.py comment confirms awareness |
| Widget JS byte-identical | ✓ Not touched this window |
| Secrets never in commits | ✓ .env.example only (placeholders) |
| Schema changes via numbered migrations | ✓ migrations/194_voice_addon.sql |

All critical rules respected.
