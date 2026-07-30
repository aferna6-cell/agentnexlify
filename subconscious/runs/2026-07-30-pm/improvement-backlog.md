# Improvement Backlog — 2026-07-30-pm

Items not selected this run, ranked by next-trigger condition.

---

## Parking Lot

### Autonomy Loop Health Check (Step 9I)
**Category:** operational  
**Trigger:** 7+ days of production autonomy loop data (earliest: 2026-08-06)  
**Blocked by:** Infrastructure too new (sweeper 2 days old)  
**Concept:** Add Step 9I to nightly SKILL.md — `python3 scripts/autonomy/run_loop.py list` summary, alert on anomalies  

### graph/runtime.py God-Class GH Issue
**Category:** code_health  
**Trigger:** `wc -l backend/graph/runtime.py` exceeds 550 lines (currently 516)  
**Blocked by:** Threshold not yet reached  
**Concept:** File GH issue for split into `runtime_core.py` + `node_executor.py` + `checkpoint_manager.py`  

### Tenant Silence Alert Workflow
**Category:** customer_value  
**Trigger:** GH Actions spending limit resolved  
**Blocked by:** GH Actions dark (Day 11+)  
**Concept:** `paying_tenant_silence.yml` GH workflow, daily check, alert if paying tenant silent >7 days. Issue #610 filed.  

### governance.json Active Directions Archive
**Category:** workflow_efficiency  
**Trigger:** active_directions exceeds 20 entries, OR age >30 days on pending_human_action items  
**Blocked by:** Not urgent; signal-to-noise manageable at current size  
**Concept:** `archived_directions` section; subconscious skill skips archived entries  

---

## Carry-Forward Tracker

| Step | Run Won | Cycle | PR | Status |
|------|---------|-------|----|--------|
| Step 9G (original) | Run 100 (2026-07-23) | 2/3 | #577 (open) | Not in SKILL.md — superseded by Step 9G-Direct |
| Step 9G-Direct | Run 102 (2026-07-30-pm) | 1/3 | — | **THIS RUN'S WINNER** |
| Step 9H | Run 101 (2026-07-30) | 1/3 | #611 (open) | Not in SKILL.md |

**Escalation rules:**  
- Step 9G-Direct cycle 3 → direct implementation (bypass recommendation)  
- Step 9H cycle 3 → direct implementation  
- KB staleness: CRITICAL TODAY — no further carry-forward, implement immediately  

---

## Owner-Action Required

| Item | Issue | Days Open | Urgency |
|------|-------|-----------|---------|
| GH Actions spending limit | #500 | 11+ | BLOCKER |
| Merge PR #577 (Step 9G + 9H) | PR #577 | 6 | HIGH — KB threshold today |
| Merge PR #611 (Step 9H morning run) | PR #611 | 0 | MEDIUM |
| REFERRAL_REWARD_ENABLED=1 | GH #413 | 10+ | MEDIUM |
| Keys Koffee business hours config | GH #415 | 10+ | LOW |
