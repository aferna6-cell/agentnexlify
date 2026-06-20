# Nightly Commit Review — 2026-06-20

Generated: 2026-06-20 UTC  
Commits reviewed: 5 (last 24 hours)

---

## Commits Triaged

| SHA | Title | Risk |
|-----|-------|------|
| `b52d8bc` | subconscious: fix memory.jsonl JSONL integrity (split merged run 58/59 line) | LOW |
| `2faac91` | subconscious: run 2026-06-19-pm — Fix GH #292/#293 plan-name dicts (run 62 mandate) | LOW |
| `2d16e20` | ops: morning-digest 2026-06-19 | LOW |
| `18b322b` | subconscious: run 2026-06-19 — Fix GH #308 webhook idempotency early-write (run 61) | LOW |
| `6310848` | ops: nightly-commit-review 2026-06-19 | LOW |

**All 5 commits are ops/planning artifacts. Zero code changes.**

---

## CLAUDE.md Compliance

- **No `from __future__ import annotations`** — N/A (no Python files changed)
- **No `tenant_id` on leads/conversations`** — N/A (no DB code changed)
- **Widget byte-identical** — not touched this run
- **Schema changes via migration files** — no schema changes
- **No secrets in commits** — PASS

---

## LOW Risk — Auto-fixed

None. No LOW-risk bugs found.

---

## HIGH Risk Carry-Over — Require Immediate Human Action

### 🔴 GH #308 — Webhook idempotency early-write drops payment events (DAY 4, 5th cycle)

**Status: STILL OPEN — unimplemented across 5 consecutive subconscious/nightly cycles**

- `check_and_record()` in `backend/services/idempotency.py` inserts row BEFORE handler runs
- Handler throws → row persists with `response_body=NULL` → Stripe retry returns 200 without processing → **event permanently dropped**
- Blast radius: tenant fixes payment card, stays dunning-locked forever
- Fix: ~10 lines. Add `delete_key()` to `idempotency.py`, call it in `stripe_webhooks.py` exception handler before re-raise
- Full sketch: `subconscious/runs/2026-06-19/winning-concept.md`
- Cannot auto-fix: touches Stripe payment handling

**Files:** `backend/services/idempotency.py`, `backend/routers/stripe_webhooks.py`

---

## MEDIUM Risk Carry-Over — Require Human Action

### 🟡 GH #292/#293 — Plan-name dicts missing chatbot/agent_os (DAY 4, run 62 mandate fired)

**Status: STILL OPEN — all 3 affected files confirmed unpatched**

- `sms_rate_limiter._UNLIMITED_PLANS` (line 10) — missing `chatbot`, `agent_os`
  - Every new paid tenant SMS-capped at 50/day regardless of plan
- `api_key_auth._ALLOWED_PLANS` (line 29) — missing `chatbot`, `agent_os`
  - Zapier integration returns 402 for all new paid tenants
- `billing_reconciliation._PLAN_AGENT_RUN_CAPS` + `_PLAN_BASELINE_AI_TOKENS` — missing both plans
  - Agent run caps and AI token baselines wrong for all new tenants

**Blocking product decision:** Should `chatbot` ($19.99) have unlimited SMS or a cap (e.g. 200/day)?  
`agent_os` ($99.99) → unlimited is safe (parity with `professional`).

Fix sketch: `subconscious/runs/2026-06-19-pm/winning-concept.md`  
Open since: 2026-06-16 (4 days, repricing day)  
Every new paid signup since 2026-06-16 is affected.

**Run 63 mandate**: if still unimplemented next cycle, subconscious switches winner back to GH #308.

---

## Summary

Quiet day — 5 commits, all ops/planning artifacts, zero product code changes. Quality high.

**Two revenue bugs remain unresolved for 4 days:**

1. **GH #308** (HIGH) — payment event permanently dropped when handler fails; tenant stays dunning-locked after fixing card. 4 days open, 5th consecutive flagging cycle. Fix is 10 lines, fully sketched.

2. **GH #292/#293** (MEDIUM) — all new paid tenants since repricing (2026-06-16) get wrong SMS limits and Zapier 402. Fix is 3 files, ~12 lines. Blocked on one product decision: chatbot SMS limit.

Both require explicit human approval. Neither can proceed autonomously.

No auto-fixes committed this run.
