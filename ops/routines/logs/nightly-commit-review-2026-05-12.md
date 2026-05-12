# Nightly Commit Review — 2026-05-12

**Reviewer:** nightly-commit-review agent  
**Window:** Last 24 hours (since 2026-05-11 ~06:00 UTC)  
**Commits reviewed:** 2  
**Auto-fixes applied:** 0  
**New GH issues filed:** 0 (1 existing issue confirmed)  

---

## Commits Triaged

### 1. `e5d077d` — subconscious: run 2026-05-11 (run 16) — Widget 3-Copy Sync Guard (moratorium day 3)
**Risk:** LOW  
**Files:** `subconscious/runs/2026-05-11/` (5 new markdown/JSON files), `subconscious/state/memory.jsonl`  
**Assessment:** Pure documentation and state tracking. No code changes, no API surface, no schema changes. Subconscious run 16 output — debate log, ideas, improvement backlog, winning concept, run summary. No bugs introduced.

### 2. `0317c08` — subconscious: run 16 governance.json corrections
**Risk:** LOW  
**Files:** `subconscious/state/governance.json`  
**Assessment:** State file corrections: `last_run` updated to 2026-05-11, `total_runs` 15→16, `widget_helpers` status upgraded `implemented_unverified` → `implemented_production_verified` (23 days production, no errors), new parking lot entries, moratorium trigger reason extended. No code, no data model changes.

---

## Environment Checks

| Check | Result |
|-------|--------|
| Widget copies in sync (widget/ ↔ frontend/public/widget/) | PASS — byte-identical |
| Widget copies in sync (widget/ ↔ landing-page-v2/widget/) | PASS — byte-identical |
| `scripts/check-widget-sync.sh` present | MISSING — moratorium item, human approval required |

---

## Issues Found (No Auto-Fix — Deferred to Human)

### [EXISTING GH #107] Zapier API key plan_status not enforced — HIGH
**File:** `backend/routers/zapier.py:86-134` (`_get_api_key_client`)  
**Finding:** The function selects `plan_status` from the `tenants` table but never evaluates it. The plan tier is enforced (`_ALLOWED_PLANS`), but not the subscription state. A cancelled tenant retaining an un-revoked API key will pass authentication and tier checks, bypassing the access gate.

```python
# plan_status fetched here but not checked:
tenant_result = db.table("tenants").select("id, plan, plan_status").eq("id", client_id)...
plan = tenant.get("plan") or "free"
if plan not in _ALLOWED_PLANS: raise 402  # only checks plan, not plan_status
# return dict omits plan_status entirely
return {"client_id": client_id, "plan": plan, "key_row": key_row}
```

**Suggested fix:** Add `plan_status IN ('active', 'trialing')` filter or post-query check. Return `plan_status` in context dict.  
**Action:** Already tracked as GH issue #107 (11+ days open). Route via issue-to-pr-loop. Do NOT auto-fix (auth/payments path — requires human approval per CLAUDE.md protocol).

---

## Subconscious Moratorium Status (Informational)

Moratorium remains active after run 16. No pending items implemented in 3 days since run 15 (May 8).

| Run | Item | Days Pending | Effort | Status |
|-----|------|-------------|--------|--------|
| 4 | AI-to-Human Handoff v1 | 25+ | M (1.5-2 days) | URGENT — requires sprint |
| 7 | Widget 3-Copy Sync Guard | 17 | S (~15 min) | Awaiting human approval |
| 8 | Wire check_project_invariants.py to pre-commit | 16 | S (~5 min) | Awaiting human approval |
| 14 | Wire lead qualifier golden eval to CI | 6 | S (~20 min) | Awaiting human approval |

All 3 S-effort items (runs 7, 8, 14) can exit moratorium in ~40 min. Widget copies currently in sync (no production risk today, but guard is still missing).

---

## Summary

No bugs to auto-fix from today's commits. Both commits are LOW risk (subconscious state/documentation). One pre-existing HIGH security issue confirmed and already tracked (GH #107 — Zapier plan_status enforcement). Moratorium remains active at 4 pending items, oldest 25 days. Widget copies currently byte-identical (no production incident).

**Recommended human action:** Implement subconscious runs 7 + 8 + 14 (40-minute sprint) to exit moratorium, then prioritize GH #107 via issue-to-pr-loop.
