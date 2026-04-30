# Nightly Commit Review — 2026-04-28

**Window:** last 24 hours from 2026-04-28 UTC  
**Commits reviewed:** 4  
**Test suite:** pytest not installed in review environment — Python syntax check PASS; vite build deps not installed  
**LOW fixes applied:** 4 (silent exception/catch logging gaps)  
**Issues created:** 0 (all items either already filed or fixed tonight)

---

## Commit Triage

| SHA | Message | Risk | Finding |
|-----|---------|------|---------|
| `549f1f1` | ops: morning-digest 2026-04-27 | LOW | Log file only, no code |
| `734cef0` | subconscious: run 2026-04-27 — JS + Python Silent Catch Guard | LOW | Analysis/docs only. Identified widget_chat.py:295 bare-except (issue #97) + 3 JS silent catches for action tonight |
| `402a44a` | Merge branch 'main' | LOW | Merge commit, no direct changes |
| `7c1c0b3` | ops: nightly-commit-review 2026-04-27 | LOW | Log file only, no code |

No new code landed in the last 24 hours — all commits were ops/docs/analysis artifacts. Active work items from prior reviews were actioned based on subconscious run evidence.

---

## LOW Fixes Applied Tonight

### Fix 1 — `widget_chat.py:299` — bare except swallows plan-lookup failure silently
**Issue:** #97 (filed 2026-04-27, MEDIUM impact — paid tenants silently rate-limited at free tier)  
**File:** `backend/routers/widget_chat.py:299`  
**Change:** `except Exception:` → `except Exception as exc:` + `logger.warning("_chat_rate_limit fallback to free tier for key=%s: %s", key, exc)`  
**Risk:** Additive only — log line added, fallback behavior unchanged  
**Verified:** Python syntax PASS (`ast.parse`)

### Fix 2 — `MarketingDashboardPage.jsx:90,96` — two silent `.catch(() => null)` 
**File:** `frontend/src/pages/MarketingDashboardPage.jsx`  
**Change:** Both catches now log `console.warn(...)` before returning null  
**Risk:** Additive only — same null return, adds browser console visibility  
**Verified:** 0 silent catches remaining (node regex scan)

### Fix 3 — `LocalSEOPage.jsx:262` — silent `.catch(() => null)` on history reload
**File:** `frontend/src/pages/LocalSEOPage.jsx`  
**Change:** Catch now logs `console.warn("LocalSEO: fetchSeoAuditHistory failed:", err)` before returning null  
**Risk:** Additive only  
**Verified:** 0 silent catches remaining (node regex scan)

### Fix 4 — `AuthContext.jsx:89` — silent `.catch(() => {})` on /me plan refresh
**File:** `frontend/src/context/AuthContext.jsx`  
**Change:** Catch now logs `console.warn("AuthContext: /me refresh failed:", err)`  
**Risk:** Additive only — /me refresh is best-effort; fallback behavior (keep JWT plan) unchanged  
**Verified:** 0 silent catches remaining (node regex scan)

---

## Critical Rule Checks

| Rule | Status |
|------|--------|
| `client_id` not `tenant_id` on leads/conversations | PASS — no DB queries touched |
| `status` not `lead_stage` | PASS — not touched |
| No `from __future__ import annotations` in FastAPI files | PASS — grep clean |
| Widget JS byte-identical | N/A — widget not touched |
| Secrets not in commits | PASS |
| Schema changes via migration files only | N/A — no schema changes |

---

## Open Issues (carry-forward from prior reviews)

| # | Severity | Summary | Status |
|---|----------|---------|--------|
| #93 | HIGH | `fraud_guard.py:121-123` pauses coupon/trial signups — revenue loss | Open |
| #94 | HIGH | `IndexError` on empty `charges.data` in billing router | Open |
| #97 | MEDIUM | `_chat_rate_limit` bare-except — **partially resolved tonight** (logging added; root cause DB reliability separate) | Logging fixed; #97 still open for index/cache follow-up |
| #98 | MEDIUM | `_find_tenant_by_phone` O(N) full table scan in twilio_webhooks.py | Open |
| #99 | MEDIUM | Stripe `SignatureVerificationError` catch anti-pattern | Open |

## Notes
- Subconscious run 2026-04-27 also recommended adding a pre-commit hook check (Check 9) for JS silent catches. That change (modifying `scripts/hooks/pre-commit`) was deferred — it requires human review to avoid blocking legitimate patterns. Recommend as a follow-up task.
- Subconscious governance correction: Lead Source Analytics (Run 2) status should be updated from "pending" to "implemented" in `subconscious/state/governance.json`.

Verified: all 4 fixes syntax/pattern-clean — PASS
