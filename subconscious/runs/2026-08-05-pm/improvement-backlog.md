# Improvement Backlog — Run 101 (2026-08-05-pm)

---

## Active (pending human approval)

### Step 9J: Accumulated-issue auto-closer [RUN 101 WINNER]
- Add Step 9J before Step 9D in nightly-commit-review SKILL.md Scheduled Task Prompt
- Close all open `loop-health` GH issues before Step 9D opens a fresh one
- AUTONOMOUS-EXECUTABLE via SKILL.md-edit channel once approved
- PR: commit onto existing `subconscious/run-101-step9g` branch (PR #626, per dedup guard)
- Status: recommended

### Step 9G: KB autopopulate self-healing trigger [4TH CYCLE CARRY-FORWARD]
- Already implemented in PRs #625 and #626 (both open, neither merged)
- KB 13 days stale. Step 9F alerting but cannot repair.
- 4th cycle without merge. Human decision required: merge ONE of #625/#626, close the other.
- Status: recommended (stalled — awaiting human merge)
- Escalation: if still unmerged by 2026-08-13 (day 21), run 102 should raise P1 issue

---

## Parking Lot

- **PR merge readiness escalation (tiered)** — day-7/day-14/day-21 escalation for
  stalled AUTONOMOUS-EXECUTABLE PRs. Promising but needs exponential-backoff mechanism.
  Park for run 102 if Step 9G still unmerged at day 21 (2026-08-13).

- **KB staleness escalation hardener (Step 9H-variant)** — create P1 GH issue after
  3 consecutive Step 9G trigger failures. Depends on Step 9G being live first. Park
  until Step 9G merges.

- **Typed KB note staleness monitoring** — query `tenant_kb_documents` for `source='note'`
  rows older than 30 days. BLOCKED: needs service-role key access from nightly runner
  (security concern). Re-evaluate if a FastAPI admin health endpoint is added.

- **LoopHealthPage.jsx** — promote from parking lot when Agent OS >5 active tenants.
  Currently 2–3 tenants.

- **Voice test regression audit** — nightly clean 3 consecutive days; 250 voice tests
  passing per nightly log. Low urgency. Revisit if voice test count drops.

- **Owner MCP quickstart doc** — human-authored content. Promote on second MCP tenant
  activation (currently 1 tenant activated).

---

## Killed This Run

- **PR tombstoning (Idea C / Step 9K)** — auto-close subconscious draft PRs older than
  14 days. KILLED: contradicts PR dedup guard intent (reuse vs. delete); removes
  evidence; root cause is approval friction, not PR count.

- **KB staleness escalation hardener (timing)** — presupposes Step 9G is live to count
  "3 consecutive trigger failures." Can't activate until Step 9G merges. Weakened.

---

## Mandate Status for This Run

| Item | Status |
|------|--------|
| Step 9G in SKILL.md? | FAIL — 0 occurrences. 4th consecutive cycle. PRs #625/#626 unmerged. |
| KB freshness since 2026-07-23? | FAIL — 13 days stale (threshold 7 days). |
| Agent OS tenant count >5? | LIKELY NO — LoopHealthPage condition not met. |
| MCP tenant count >5? | LIKELY NO — Step 9H killed, 1 tenant activated. |
