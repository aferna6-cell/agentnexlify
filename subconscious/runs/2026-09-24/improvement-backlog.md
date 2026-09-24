# Improvement Backlog — Run 128 (2026-09-24)

## Active Direction

### Step 9J Priority Queue (run 128 winner)
**Status:** Recommend — autonomous-executable
**Carry:** 1
**Evidence:** 7+ runs, 17/19 Dependabot PRs skipped per run
**Action:** Add `sort: "created"`, `direction: "asc"`, `perPage: 5` to Step 9J.1 search call in SKILL.md
**Category:** workflow_efficiency

---

## Parking Lot (valid, not yet winner)

### GH #881 Spec Enhancement (Idea 2)
**Status:** Parked — blocked by AUTOPILOT_GH_TOKEN expiry
**Reason:** os_tool_executions.py split can't execute until GH #399 resolves. Spec enhancement value depends on token rotation within 8 days.
**Revisit when:** GH #399 closes (token rotated) OR nightly review reaches Step 9L with time to post comment.

### Step 9M — AI Metering Violation Trend Tracking (Idea 4)
**Status:** Parked — lower priority than Step 9J
**Reason:** 45 violations tracked in GH #827. Trend detection adds value but depends on issue-to-pr-loop being active (blocked by GH #399). No mechanism to act on trend data until loop resumes.
**Revisit when:** AUTOPILOT_GH_TOKEN rotated and loop resumes.

### GH #403/#616/#618 Consolidation (Idea 5)
**Status:** Parked — operational, not structural improvement
**Reason:** Valid human-attention optimization but single-use comment with no SKILL.md persistence. Belongs in nightly actions log, not subconscious winning concept.
**Revisit when:** Never as subconscious winner; nightly can post it as a side action.

---

## Frozen (do not revisit)

### ai_human_handoff
**Reason:** Customer gap exists but GH #399 blocks issue-to-pr-loop. Frozen until loop active.

### widget_drift_topic
**Reason:** Retired run 125. CI enforces byte-identity. No subconscious attention needed.

### Step 9O — Credential Liveness Test
**Reason:** KILLED run 128 debate. Step 9E P0 covers the urgency signal. No evidence of early revocation risk. Token budget pressure argues against adding steps. Revisit only if Step 9E EXPIRED state fires without human action.

---

## Resolved (last 10 runs)

| Run | Winner | Status |
|-----|--------|--------|
| 128 | Step 9J Priority Queue | Recommend |
| 127 | Step 9E P0 Tier | **IMPLEMENTED** by nightly-2026-09-24 |
| 126 | Step 9G gh→MCP fix | **IMPLEMENTED** by nightly-2026-09-23 |
| 125 | Step 9L AI metering coverage | IMPLEMENTED (carried 3 runs) |
| 124 | Step 9K KB staleness self-heal | IMPLEMENTED |
| 123 | Step 9J Dependabot auto-merge | IMPLEMENTED (base step) |
| 122 | Step 9I SUPABASE_ACCESS_TOKEN check | IMPLEMENTED |
| 121 | Step 9F credential schedule expansion | IMPLEMENTED |
| 120 | Step 9E credential check | IMPLEMENTED |
| 119 | Step 9C/9D log format standardization | IMPLEMENTED |

---

## P0 Alert (for next run mandate check)

**AUTOPILOT_GH_TOKEN expires 2026-10-02 (8 days from run date).**
- GH #893 closed "not_planned" — not the right tracking issue
- GH #399 open (19 comments, 0 human action) — active escalation thread
- Step 9E P0 firing daily escalations
- Brain connector GitHub PAT also expires 2026-10-02
- Human action required before 2026-10-02 or all automation stops
