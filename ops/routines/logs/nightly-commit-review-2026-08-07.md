# Nightly Commit Review — 2026-08-07

**Run time:** 2026-08-07 (automated, 2:37 AM cadence)  
**Commits reviewed:** 3 (last 24h)  
**Issues found:** 2 (1 LOW fixed, 1 MEDIUM filed)  
**KB staleness:** 15 days — Step 9G triggered

---

## Commits

### 1. `f48cffc` — ops: morning-digest 2026-08-06
**Risk: LOW**  
Single log file addition. No code changes. No action needed.

---

### 2. `e0e9be6` — feat: competitor-inspired insights (#639) [skip ci]
**Risk: MEDIUM (new endpoints + Stripe payment surface)**  
Owner-approved merge. 22 files, 1528 insertions. New routers: `appointment_briefs`, `billing_usage`, `insights`. New services: `appointment_brief`, `daily_focus`, `response_score`.

**Checks passed:**
- No `from __future__ import annotations` in any new FastAPI files ✓
- No `lead_stage` or `service_interest` column references ✓
- Uses `status` correctly for lead pipeline ✓
- All DB queries use `tenant_select()` — handles `client_id`/`tenant_id` mapping via `_TENANT_COLUMN_OVERRIDES` ✓
- `lead_temperature` column valid (migration 094, indexed) ✓
- `verify_tenant()` applied on all new routes ✓
- New routers registered in `main.py:938,940,950` ✓

**Issue found — MEDIUM: Missing `block_demo_role` on `POST /api/v1/billing/buy-usage`**
- `billing.py` guards all Stripe endpoints with `block_demo_role` at router level
- `billing_usage.py` `buy-usage` endpoint creates a $24.99 Stripe Checkout session with no demo guard
- Demo-role users can call the endpoint and reach Stripe
- Filed: **GH #640** (`nightly-review`, `security`, `medium-risk`)
- **Fixed directly** (pre-push hook blocked push until resolved): added `dependencies=[Depends(block_demo_role)]` to `@router.post("/buy-usage")` + import

**Issue found — LOW: Unused import `current_period_month` in `billing_usage.py:16`**
- `current_period_month` imported from `ai_usage_guard` but never referenced in the file
- **Fixed directly:** removed from import line → committed in this nightly run

---

### 3. `fc2dd7d` — subconscious: run 2026-08-06-pm (101)
**Risk: LOW**  
Adds Step 9G to `nightly-commit-review/SKILL.md` (KB self-healing trigger). Subconscious run output files. Governance JSON update. No production code touched.

**Step 9G verified:** Logic is correct — triggers `kb-autopopulate.yml` when staleness > 7 days, checks status, reports via GH #403 on failure.

---

## Step 9F/9G — KB Staleness

**Last successful KB populate:** 2026-07-23 (per `knowledge-base/log.md`)  
**Days stale:** 15 (threshold: 7 days)  
**Action:** Step 9G triggered.

**Trigger result:** `gh workflow run kb-autopopulate.yml` — 204 No Content (queued successfully)

**Status check:** New run not yet reflected in run list (queued). Recent runs #269-#271 (all today, 2026-08-07T05:15-06:44Z) show `conclusion: success` — but KB log shows no entries since 2026-07-23. This matches the prior silent-failure pattern (workflow exits 0 via `continue-on-error:true` despite missing ANTHROPIC_API_KEY / VOYAGE_API_KEY / SUPABASE_ACCESS_TOKEN). The fix from 2026-07-09 should now file a human-action-required issue on failure instead of silently passing.

**Step 9G log:** `Step 9G: kb-autopopulate trigger attempted — conclusion: pending (new run not yet in run list)`

**Recommendation:** Check GH Actions for the newly-triggered run. If it fails, verify ANTHROPIC_API_KEY, VOYAGE_API_KEY, SUPABASE_ACCESS_TOKEN are set in GitHub Actions Secrets. See GH #403 for history.

---

## Summary

| Commit | Risk | Action |
|--------|------|--------|
| `f48cffc` morning-digest | LOW | None needed |
| `e0e9be6` insights feat | MEDIUM | GH #640 filed (demo guard); unused import fixed |
| `fc2dd7d` subconscious | LOW | None needed |

**Fixes committed this run:**
- `backend/routers/billing_usage.py`: removed unused `current_period_month` import
- `backend/routers/billing_usage.py`: added `block_demo_role` guard to `POST /buy-usage` (pre-push hook required this before push)

**Issues filed:**
- GH #640 — MEDIUM: `buy-usage` missing `block_demo_role` guard (fixed in same run)

**KB:** autopopulate triggered (15d stale), status pending
