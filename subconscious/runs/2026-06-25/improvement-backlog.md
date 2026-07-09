# Improvement Backlog — Run 66 (2026-06-25)

## Promoted to Active (run 66 winner)

- **Escalate run 65 delivery — add explicit nightly trigger instruction (AUTONOMOUS-EXECUTABLE)**
  - Confidence: HIGH, Effort: S, Category: workflow
  - Mandate: Run 66 mandate fires (run 65 not implemented by nightly 2026-06-24)

## Parking Lot Updates

### Promoted (from run 65 Bonus A)

- **Plan-name invariant guard Check 7 to check_project_invariants.py**
  - ROI: 2.2 (was Bonus A in run 65)
  - Sequencing: blocked until run 65 lands (exits 0)
  - AUTONOMOUS-EXECUTABLE, S-effort (~10 min)
  - Run 67 candidate once run 65 confirmed

### Retained from prior runs

- **AI-to-Human Handoff v1** (run 4/38)
  - Day 70, Critical, M-effort, human required
  - Moratorium blocks until true_pending ≤ 2
  - Highest customer-value item in queue

- **email_sequences.py god-class split** (run 41)
  - ~1143L, M-effort, human required
  - Prerequisites: god-class-splitter SKILL.md ✓, post-split-test-repair SKILL.md ✓
  - Blocked: moratorium + pre-commit Check 13 (both resolve after run 65)

- **Cleanup sprint** (runs 20/21/29/42/50)
  - ~1h combined, drops pending ~5→≤3
  - Prerequisite: run 65 lands first (commits unblocked)

- **GH #263 — 24 pending migrations investigation** (run 62 parking lot)
  - ROI: 2.3, triage required
  - Deferred: insufficient evidence to scope fix

- **Zapier API key plan_status enforcement** (GH #107)
  - ROI: 2.5, HIGH security
  - Route via issue-to-pr-loop, not subconscious winner

- **kb-autopopulate.sh fix** (run 54 parking lot)
  - ROI: 1.8, agent-browser CLI not installed
  - KB stale 50+ days — growing urgency

- **Cross-tenant isolation test for os_graph_memory** (run 54 parking lot)
  - ROI: 2.1, deferred until next Agent OS sprint

- **Add tenant scope registration checklist to schema-discipline.md** (run 54 parking lot)
  - ROI: 2.0, path-scoped rule addition

### Killed this run

- **Vercel deploy quota** — killed, insufficient evidence (single brain note, likely self-resolving). Recurrence threshold: 3 events in 7 days before promoting to parking lot.

## Priority Stack (post-run 66)

1. → nightly delivers run 66 SKILL.md edit + run 65 fix (AUTONOMOUS-EXECUTABLE)
2. → Add plan-name guard Check 7 (run 67 candidate, AUTONOMOUS-EXECUTABLE)
3. → Human: AI-to-Human Handoff v1 (run 4/38, highest customer value)
4. → Human: email_sequences.py split (run 41)
5. → Cleanup sprint (runs 20/21/29/42/50) → moratorium exits
6. → Post-moratorium: new feature recommendations

## Moratorium status

- Active (true_pending ~5-6 > threshold 2)
- Max pending age: run 4 at day 70 (2026-06-25)
- Exit path: AI-to-Human (day) + email_sequences (2h) + cleanup sprint (1h) → pending ≤2
