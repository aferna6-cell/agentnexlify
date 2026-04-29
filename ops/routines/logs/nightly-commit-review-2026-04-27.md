# Nightly Commit Review — 2026-04-27

**Window:** last 24 hours from 2026-04-27 UTC  
**Commits reviewed:** 10  
**Test suite:** pytest not installed in review environment — merge commit `50123a4` verified 37/37 pass before merge  
**Issues created:** 3 MEDIUM (GitHub #97, #98, #99)  
**LOW fixes applied:** 0 (no actionable LOW-risk bugs found)

---

## Commit Triage

| SHA | Message | Risk | Finding |
|-----|---------|------|---------|
| `50123a4` | Merge feature/steal-list-1-6 into main | LOW | Merge commit only, no direct changes |
| `a9a677e` | test(rate-limit): lock _chat_rate_limit signature contract | LOW | Tests only, clean |
| `ee4bc16` | fix(widget-chat): correct _chat_rate_limit signature for slowapi | LOW | Production crash fix (TypeError on every widget request), already shipped and verified |
| `752819c` | Merge pull request #96 | LOW | Merge commit only |
| `841b987` | chore(claude): cost-optimization moves | LOW | Docs/rules only — effort-per-prompt, one-task-one-chat, usage-observability |
| `041b7f0` | chore(claude): subagent spawn discipline + dedicated tools index | LOW | Docs/rules only — model-routing, pdf-handling, CLAUDE.md |
| `cf0fd7f` | Merge pull request #95 | LOW | Merge commit only |
| `fb57995` | fix(idempotency,rate-limit): close race + RLS + XFF spoofing | HIGH | Three HIGH issues patched (atomic upsert race, RLS on idempotency_keys, XFF spoofing). Three items explicitly deferred by developer → issues #97, #98, #99 |
| `b0b1fb4` | feat(steal-list 1-6): idempotency, rate-limit, contextual reindex, MCP tooling | MEDIUM | New rate-limit middleware, idempotency service, migrations 114/115, reindex script. Code quality good; deferred items tracked in issues |
| `b50e198` | chore(ai): auto-commit Claude edits [main 2026-04-26 11:18] | MEDIUM | Stripe/Twilio webhook idempotency wiring, new scripts (rules-doctor, agent-linter). SignatureVerificationError anti-pattern → issue #99 |

---

## Issues Created

### #97 — MEDIUM — `_chat_rate_limit` swallows exceptions silently
**File:** `backend/routers/widget_chat.py` ~line 295  
**Commit:** `ee4bc16`, `b0b1fb4` (deferred from `fb57995`)  
**Finding:** Bare `except Exception: plan = "free"` with no log statement. Paid tenants silently rate-limited at free-tier (30 rpm) if DB lookup fails; impossible to detect from logs.  
**Fix:** Add `logger.warning("_chat_rate_limit fallback to free tier for key=%s: %s", key, exc)`.

### #98 — MEDIUM — `_find_tenant_by_phone` O(N) full table scan
**File:** `backend/routers/twilio_webhooks.py:69`  
**Commit:** Pre-existing, called by `b0b1fb4` idempotency work (deferred from `fb57995`)  
**Finding:** Loads up to 50 tenant rows on every inbound SMS/voice webhook and does in-Python phone normalization. The `.limit(50)` cap silently drops tenants >50.  
**Fix:** DB index on normalized phone; or in-process LRU cache with TTL.

### #99 — MEDIUM — Stripe `SignatureVerificationError` catch anti-pattern
**File:** `backend/routers/stripe_webhooks.py` ~line 46  
**Commit:** `b50e198` (deferred from `fb57995`)  
**Finding:** `except (stripe.SignatureVerificationError, Exception) as exc` with `if "SignatureVerification" in type(exc).__name__` — since `SigVerErr` is a subclass of `Exception`, the union collapses to `Exception` and the specific branch never fires. Bad signatures may return 500 instead of 400.  
**Fix:** Split into ordered `except` clauses (most specific first).

---

## Critical Rule Checks

| Rule | Status |
|------|--------|
| `client_id` not `tenant_id` on leads/conversations | PASS — new code only touches `tenants`, `idempotency_keys`, `widget_configs` tables |
| `status` not `lead_stage` | PASS — not touched |
| No `from __future__ import annotations` in FastAPI files | PASS — grep clean |
| Widget JS byte-identical | N/A — widget not touched this window |
| Secrets not in commits | PASS — only `docs/env-vars-2026-04-26.md` documents var names, no values |
| Schema changes via migration files only | PASS — migrations 114, 115, 116 all properly numbered |

---

## Notes
- Migrations 114 and 115 were flagged "NOT YET APPLIED" in `b0b1fb4`. Migration 116 (RLS) was part of `fb57995`. Verify all three are applied in Supabase before next deploy.
- `scripts/reindex_contextual.py` is new (278 lines); no issues found on review but it makes direct Supabase calls — ensure `SUPABASE_SERVICE_ROLE_KEY` is set in the environment where it runs.
- Two pre-existing HIGH billing issues from yesterday's review remain open: #93 (coupon/trial paused), #94 (IndexError on empty charges.data).
