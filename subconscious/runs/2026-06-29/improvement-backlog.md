# Improvement Backlog — Run 71 (2026-06-29)

## Winner (run 71)
- **KB autopopulate fix** — AUTONOMOUS-EXECUTABLE, 2-line change, 53+ days broken, HIGH confidence

## Parking Lot Updates

### Promoted to run 72+ candidates (from this run's debate)
- **Record Audit Dashboard** — backend exists (record_audit.py, council sprint), no UI. S-effort. Nightly's own estimate: run 72. Pre-condition: SMS Compliance Dashboard (run 70 winner) must be implemented first.
- **Schema-discipline checklist** (5-question "New Table Checklist" in .claude/rules/schema-discipline.md) — AUTONOMOUS-EXECUTABLE, XS effort, parking lot ROI 2.0. No new occurrence since run 54 (19 runs ago). Promote when next Agent OS service ships.

### Standing Queue (already tracked, not re-recommended)
- **AI-to-Human Handoff v1** (run 4/38, pending_approval, 75+ days) — Critical customer gap, all 7 industries. Human-required. Blocked by moratorium.
- **Email sequences split** (run 41, pending_approval, 30+ days) — invoke /god-class-splitter. Human-required. Blocked by moratorium.
- **SMS Compliance Dashboard** (run 70, pending_approval) — S-effort, backend ready. Human-required. First item in human queue.

### Parking Lot (not this run)
- **Zapier #107 plan_status enforcement** — ROI 2.5, security bug, route via issue-to-pr-loop (not subconscious winner queue per parking lot note)
- **Fix email_sequences N+1 queries** — GH #112, M-effort, post-moratorium
- **Cross-tenant isolation test for os_graph_memory** — ROI 2.1, deferred until next Agent OS sprint
- **Moratorium exit path** — still active (true_pending ~6 > max_pending_approvals: 2). Exit requires human to implement SMS Dashboard + AI-to-Human Handoff + email split → true_pending drops to ≤2

## Moratorium Status
Active. true_pending ~6 (human-required: runs 4/38/41/70 + others superseded). Max allowed: 2.
Exit path: human executes SMS Dashboard (S-effort) → AI-to-Human Handoff v1 (M-effort) → email sequences split (M-effort) → true_pending ≤ 2 → exit.

## check_project_invariants.py Status
Still exits 1 (widget drift: `landing-page-v2/widget/agentnexlify-widget.js` != `widget/agentnexlify-widget.js`).
Fix: `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
Human-only. See `docs/reminders/widget-drift-URGENT.md`. Topic retired from subconscious permanently.
