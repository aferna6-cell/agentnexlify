# Run 104 — Improvement Backlog (2026-08-15)

## Status key
- AUTONOMOUS-EXECUTABLE — nightly can apply without human approval
- PENDING-APPROVAL — human must approve before execution
- IN-PROGRESS — being worked on
- BLOCKED — external dependency (e.g., expired token, missing secret)
- CARRY-FORWARD — won a prior run, not yet implemented

---

## Active backlog (ranked by implementation readiness)

| # | Title | Category | Effort | Status | Source |
|---|-------|----------|--------|--------|--------|
| 1 | Add SUPABASE_ACCESS_TOKEN to credential rotation schedule | operational | XS | AUTONOMOUS-EXECUTABLE | Run 104 winner |
| 2 | Create route-security-guard-audit SKILL.md | code_health | S | CARRY-FORWARD (3rd cycle → AUTONOMOUS-EXECUTABLE if unimplemented at run 106) | Run 102 winner |
| 3 | scoring_config.py add block_demo_role | security | S | PENDING-APPROVAL (open GH issue) | Run 104 debate finding |
| 4 | Step 9I paying-tenant 0-conversation alert | operational | M | PENDING-DESIGN (headless Supabase MCP unconfirmed) | Run 104 idea 4 |
| 5 | Wire PR #653 draft → ready-for-review | security | XS | BONUS-ACTION (one-off) | Run 103 + 104 carry |

---

## Blocked (human-action-required)

| # | Title | Blocker | Issue |
|---|-------|---------|-------|
| B1 | Resume brain connector | GitHub PAT + SUPABASE_ACCESS_TOKEN rotation needed | #394 (23d open) |
| B2 | Resume autopilot issue-to-PR loop | AUTOPILOT_GH_TOKEN expired | #399 (37d open) |
| B3 | KB autopopulate resume | ANTHROPIC_API_KEY missing in GH Actions | #403 (37d open) |
| B4 | Close GH #643 (appointment_briefs.py security) | PR #653 needs human review+merge | #643 (8d open) |
| B5 | Provision INTEGRATIONS_ENC_KEY | Railway migration 176 blocked | #536 |

---

## Frozen

| Title | Reason |
|-------|--------|
| AI-to-human handoff | Frozen per governance — not in scope this phase |
| Widget drift | FORBIDDEN from subconscious permanently (widget_drift_topic_retired: true) |

---

## Parking lot (not yet ready to ideate)

- **Step 9I paying-tenant 0-conversation alert**: Supabase MCP availability in headless nightly sessions is unconfirmed. Monitor before writing the step — if headless MCP can't query the DB, the step is unimplementable without a new architecture.
- **response_score.py**: Nexlify Score lives in two files — `backend/routers/scoring_config.py` (scoring factor CRUD) and `backend/routers/leads.py` (lines 133/144 score-all/score-one endpoints). ai_usage_guard audit of scoring_config.py surfaced the block_demo_role gap now tracked as item #3 above.
- **Nightly consecutive-commit-zero**: Third day without production commits on 2026-08-15 nightly. May reflect weekend cadence. Monitor another cycle.
- **KB article compile**: Step 9G triggered kb-autopopulate.yml on 2026-08-15. If #403 resolved, this should auto-recover. Monitor outcome before adding new recovery logic.

---

## Completed (last 5 runs)

| Run | Winner | Status |
|-----|--------|--------|
| 099 | Step 9F KB staleness alert | IMPLEMENTED (in nightly SKILL.md) |
| 100 | Step 9G self-healing KB trigger | IMPLEMENTED (in nightly SKILL.md) |
| 101 | Step 9G KB autopopulate direct-impl | IMPLEMENTED (PR open) |
| 102 | Create route-security-guard-audit SKILL.md | CARRY-FORWARD (3rd cycle at run 105) |
| 103 | Add brain-connector age gate to Step 9C | IMPLEMENTED same-day (nightly 2026-08-15, commit 60499dd) |
| 104 | Add SUPABASE_ACCESS_TOKEN to rotation schedule | RECOMMENDED (this run) |
