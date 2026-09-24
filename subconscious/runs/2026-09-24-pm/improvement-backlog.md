# Improvement Backlog — Run 2026-09-24-pm (Run 129)

## Active (carry-forward to run 130)

### Step 9J Priority Queue (2nd carry)
- Status: RECOMMENDED (1st carry run 128, 2nd carry run 129)
- Effort: XS
- Channel: autonomous-executable
- Action: Add `sort: 'created', direction: 'asc', perPage: 5` to Step 9J.1 search_pull_requests
- Blocked by: nothing

---

## Pending (debate survivors, not yet winning)

### Step 9G KB Failure Diagnostics
- Status: SURVIVES MODERATE (run 129 debate)
- Effort: S
- Channel: autonomous-executable (SKILL.md edit)
- Action: Poll kb-autopopulate.yml run status 30s after trigger, post specific error to GH #403
- Value: Converts silent failure to actionable GH comment; KB 29d stale
- Deferred: Implement after Step 9J is executed and cleared

### Step 9E Expiry State File
- Status: NEW (run 129 idea, not debated to top 3)
- Effort: S
- Action: Add STALE_DATE warning to Step 9E when last_rotated == expiry date exactly
- Deferred: Low priority vs AUTOPILOT_GH_TOKEN rotation (human must act first)

---

## Killed This Run

### Step 9M AI Metering Trend Tracking
- Status: WEAKENED (run 129 debate)
- Reason: billing+ai-ready label conflates new detections with regressions; premature instrumentation while 45 violations still open
- Revisit: after GH #827 violation count stabilizes

### GH #403 Consolidated Diagnostic Comment
- Status: One-time action (not a SKILL.md improvement)
- Reason: operational one-shot, not a compounding loop improvement
- Deferred: Can be executed manually by human or as a one-off nightly action

---

## Frozen (permanently)

- ai_human_handoff — rejected 3+ times, frozen per governance

---

## P0 Items (human action required, not improvable by subconscious)

- AUTOPILOT_GH_TOKEN expires 2026-10-02 (8 days) — GH #399
- Brain connector GitHub PAT expires 2026-10-02 (8 days)
- SUPABASE_ACCESS_TOKEN rotation date unknown
- ANTHROPIC_API_KEY missing from GH Actions (blocks kb-autopopulate.yml) — GH #403
