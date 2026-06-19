# Morning Digest — 2026-06-19

Generated: 2026-06-19 UTC | Caveman mode.

---

## Commits (last 24h) — 18 landed

- `18b322b` subconscious: run 2026-06-19 — Fix GH #308 webhook idempotency early-write (run 61)
- `6310848` ops: nightly-commit-review 2026-06-19
- `3030583` subconscious: run 2026-06-18-pm — Fix GH #308 webhook idempotency early-write (run 60)
- `871ba66` Leadgen: add keyless OpenStreetMap source (Google Maps fallback)
- `b0e11d0` Leadgen: merge_leads.py (dedup across runs) + Instantly-ready export
- `48a747b` Outreach runbook + onboarding email-gate check + mobile hours-row fix
- `737f02a` Security + activation: redirect-revalidating fetch + embed first-lead promise
- `3d2bd3e` Audit: security pass on recent endpoints (signup_alert, lead_alerts, os_*, instant_kb)
- `645b323` Security: consolidate SSRF guard onto url_validation + harden + cover leadgen
- `acb4cb7` Onboarding: apply migration 154 + demo-to-signup carry + talk-to-AI shortcut + Auto-KB empty fallback
- `d977341` CI: throttle high-frequency scheduled crons to conserve Actions minutes
- `01d72ed` CI: local gate mirror + trim double-spending workflow trigger
- `3732d52` Audit: signup to first-value path (item #4)
- `9bb63de` Demo: personalize /demo per lead + attribution + wire lead-engine demo_url
- `4f18e09` Alert: email the founder on every new signup
- `852ebe4` CI: re-trigger PR Validation (GHA startup flake retry 2)
- `519bd44` CI: re-trigger PR Validation (GHA infra flake)
- `ae382f5` Lead engine + cold-email sequences for outreach

Quality note: Security sprint (SSRF consolidation, redirect re-validation) looks solid. Migration 154 applied. Active leadgen + outreach tooling landed. No CLAUDE.md violations flagged by nightly review.

---

## Issues — Open / Active (top 10 by recency)

- **#337** [OPEN] Nightly commit review 2026-06-19
- **#332** [OPEN] Morning digest 2026-06-18
- **#330** [OPEN] Human legal review: TermsOfService section 4 rewritten (payment terms + failed-payment clause) — needs human sign-off
- **#329** [OPEN] Apply migration 154 (conversation sentiment + intent) to **production** — not yet applied
- **#308** 🔴 [OPEN] MEDIUM: Webhook idempotency early-write drops events on handler failure — **3 consecutive subconscious cycles flagging, still not fixed. Run 62 mandate: if unimplemented, pivot to #292/#293.**
- **#293** [OPEN] MEDIUM: orchestrator + billing_reconciliation use stale plan names after repricing (chatbot/agent_os missing)
- **#292** [OPEN] MEDIUM: sms_rate_limiter + api_key_auth missing new plan names — new paid tenants get wrong SMS limits + can't use Zapier
- **#266** [OPEN] Security: finish integrations-secret encryption — backfill + sunset plaintext columns
- **#265** [OPEN] Deps: re-raise fastapi <0.136 cap once starlette bumped to 0.50-compatible
- **#263** 🔴 [OPEN] Schema Sync CRITICAL: 24 pending migrations — flagged 2026-06-14, still open

---

## Open PRs Needing Action

- **PR #333** — main-pending: **51 commits** — billing repricing, AI Workforce, Conversation Insights, checkout hardening. Large batch. Needs review + merge decision.
- **PR #328** — Billing: save-offer step before cancel (retention, self-serve). Actionable feature.
- **PR #327** — AI Workforce: upgrade prompt on 402 (not a raw error). Small fix.
- **PR #325** — Checkout fixes: kill Stripe Link emails + land paid customers on dashboard. Critical UX.
- **PR #286** — Agent OS fail/abstain alerts + email-routed support form.
- **PR #284** — chore(deps): update python-jose ≥3.5.0
- **PR #283** — chore(deps): bump uvicorn 0.34→0.49
- **PR #282** — chore(deps): update stripe ≥15.2.1
- **PR #281** — chore(deps-dev): bump @vitest/coverage-v8 4.1.8→4.1.9 (demo-platform)
- **PR #280** — chore(deps): bump react 18→19 in demo-platform

Action needed on #333 (51-commit batch), #325 (checkout UX), #328 (retention).

---

## Subconscious Recommendation (run 61 — 2026-06-19)

**GH #308 — Fix webhook idempotency early-write.** HIGH confidence. ~20 min, 2 files, ~10 lines.
- `idempotency.py`: add `delete_key()` — deletes row before re-raising on handler failure
- `stripe_webhooks.py`: call `await delete_key(db, idempotency_key)` in exception handler
- Without fix: Stripe retries find existing row → return 200 without processing → payment events permanently lost → tenants stay dunning-locked after card fix
- Bug introduced: `47c7f8b` (2026-06-16). 3 consecutive subconscious cycles. Moratorium override (revenue).
- **Run 62 mandate**: if still unimplemented, pivot to #292/#293 (chatbot/agent_os plan-name gaps, ~10 min).

---

## Top 3 Priorities Today

1. **Fix GH #308** — Stripe webhook idempotency bug. Payment events silently dropped. 20 min, ~10 lines. Subconscious has flagged 3 consecutive runs. Fix now or pivot to #292/#293.
2. **Review + merge PR #333** — 51-commit main-pending batch. Billing repricing + AI Workforce + checkout hardening. Biggest outstanding PR. Needs eyes before it drifts further.
3. **Fix #292/#293** — chatbot/agent_os plan names missing from sms_rate_limiter + api_key_auth + billing_reconciliation. New paid tenants broken. ~10 min fix.

Bonus: Apply migration 154 to production (#329). Legal review on #330 (human required).

---

## Knowledge Base

KB log stale (last entry 2026-05-05). Embedding errors recurring (Supabase MCP unauthorized + no VOYAGE_API_KEY in cron env). 87 articles compiled, embeddings not synced. Needs credential fix.
