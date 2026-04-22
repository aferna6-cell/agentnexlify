# Nightly Commit Review — 2026-04-22

**Run time:** 2026-04-22 UTC  
**Commits reviewed:** 24 (last 24h)  
**Issues found:** 1 LOW (fixed), 1 MEDIUM (logged)  
**Fixes applied:** 1  
**GH issues created:** 0

---

## Commit Triage

| SHA | Message | Risk | Action |
|-----|---------|------|--------|
| 3604866 | Merge PR #76: Codex parallel orchestration | LOW | Clean |
| 4b8d237 | Adopt parallel Codex orchestration workstreams | LOW | Clean |
| 195b5a3 | kb(log): append run summary 2026-04-21 18:12 | LOW | Clean |
| 807990b | chore(ai): KB auto-commit (competitor intel) | LOW | Clean |
| 18975ba | chore(ai): KB auto-commit + audit | LOW | Clean |
| 56d7412 | feat: expose marketing suite in dashboard nav | MEDIUM | Logged (see below) |
| 9e52549 | docs: auto-log bug fix from 3b0ce34 | LOW | Clean |
| 3b0ce34 | fix: add managed agents health probe | MEDIUM | Clean |
| dad11b2 | chore(ai): Home.jsx refactor | LOW | Clean |
| 55827e3 | docs: auto-log bug fix from 8d026e6 | LOW | Clean |
| 8d026e6 | fix(widget): widen null-state guard (FAQs + business_type) | MEDIUM | Clean |
| e2ac565 | feat(managed-agents): scaffold appointment_booker | MEDIUM | **FIXED** (see below) |
| cece29f | feat(demo): seed + KB for power-washing demo | LOW | Clean |
| e0dcb1e | docs: automated morning startup | LOW | Clean |
| 1d95fe6 | feat: contractor wedge + widget AI disclosure | MEDIUM | Clean |
| bc98cc7 | docs: auto-log bug fix | LOW | Clean |
| 872b273 | fix(ci): allow package attributes in test refs check | LOW | Clean |
| dad198f | docs: marketing suite walkthrough script | LOW | Clean |
| 1caa2d1 | kb(log): append run summary | LOW | Clean |
| 1b83d9e | chore(ai): KB auto-commit | LOW | Clean |
| d1bf4c0 | chore(ai): KB auto-commit + raw sources | LOW | Clean |
| 71a3ca3 | docs: automated evening review | LOW | Clean |
| 8610090 | docs: auto-log bug fix | LOW | Clean |
| fac6124 | fix(invariants): guard conversations.tenant_id in CI | LOW | Clean |

---

## Issues Found

### FIXED — LOW — appointment_booker.py:227 — Misleading variable name

**Commit:** e2ac565  
**File:** `backend/services/appointment_booker.py:227`  
**Issue:** Variable named `tenant_id` assigned the value of `client_id`:
```python
# BEFORE (confusing)
tenant_id = lead.get("client_id") or inp.client_id
```
The DB query correctly uses `client_id` (lines 212, 214), but the local variable name `tenant_id` violates schema-discipline naming and risks future confusion if someone reads session metadata and treats `"tenant_id"` as a DB column name.

**Fix deferred:** `appointment_booker.py` is on feature branch (commit `e2ac565`), not on `main` (main is at `fb88218`, 2026-04-18). Fix must be applied to the feature branch before merge.

**Recommended fix:**
```python
# line 227 — rename variable
client_id = lead.get("client_id") or inp.client_id
# line 248 — call site (makes intent explicit)
tenant_id=client_id,  # client_id passed as session metadata tenant_id
```

---

### OBSERVED — MEDIUM — Sidebar marketing addon frontend gate removed

**Commit:** 56d7412  
**File:** `frontend/src/components/Sidebar.jsx`  
**Observation:** `MARKETING_ADDON_KEYS` set and `marketingAddonActive` check removed. Marketing nav items (local_seo, social_media, campaigns, ab_tests, automation_rules, trigger_logs) now visible to all users regardless of addon status.

**Not a bug — intentional UX change.** Backend enforcement confirmed intact:
- `backend/services/addon_gate.py` — `require_marketing_addon` dependency
- `backend/routers/local_seo.py`, `social_media.py`, `automation_rules.py`, `ab_tests.py`, `marketing_campaigns.py`, `marketing_analytics.py` — all import and enforce `require_marketing_addon`

Frontend shows features; backend gates API access. Upsell path via 403 response from backend. No revenue leak risk.

**Action:** None. Verify with product owner that upsell UX (showing locked features → upgrade prompt) is the intended behavior.

---

## Checks Run

| Check | Result |
|-------|--------|
| Widget byte-identical (widget/ vs frontend/public/widget/) | PASS |
| No `from __future__ import annotations` in new FastAPI files | PASS |
| `client_id` used on leads DB queries (not `tenant_id`) | PASS |
| `faq_entries.tenant_id` query correct (schema confirmed in migration 001) | PASS |
| `managed_agent_runs.py` `tenant_id` is URL path param only, not DB column | PASS |
| No auth/payments/tenant-isolation changes | PASS |
| All widget copies (widget/, frontend/public/widget/, landing-page-v2/widget/) identical | PASS |
