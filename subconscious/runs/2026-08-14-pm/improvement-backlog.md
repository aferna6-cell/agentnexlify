# Run 103 — Improvement Backlog (2026-08-14-pm)

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
| 1 | Add brain-connector age gate to Step 9C | operational | S | AUTONOMOUS-EXECUTABLE | Run 103 winner |
| 2 | Create route-security-guard-audit SKILL.md | code_health | S | CARRY-FORWARD (2nd cycle → PENDING-APPROVAL) | Run 102 winner |
| 3 | Step 9H v2: Idempotent stale-PR alerter | operational | M | PENDING-DESIGN | Run 103 idea 4 |
| 4 | Diagnose Nexlify Score ai_usage_guard path | security | S | PENDING-EXECUTION | Run 103 idea 3 |
| 5 | Promote PR #653 draft → ready-for-review | security | XS | BONUS-ACTION | Run 103 idea 5 |

---

## Blocked (human-action-required)

| # | Title | Blocker | Issue |
|---|-------|---------|-------|
| B1 | Resume autopilot issue-to-PR loop | AUTOPILOT_GH_TOKEN expired | #399 (36d open) |
| B2 | KB autopopulate resume | ANTHROPIC_API_KEY missing in GH Actions | #403 (36d open) |
| B3 | Close GH #643 (appointment_briefs.py security) | PR #653 needs human review+merge | #643 (7d open) |
| B4 | Provision INTEGRATIONS_ENC_KEY | Railway migration 176 blocked | #536 |

---

## Frozen

| Title | Reason |
|-------|--------|
| AI-to-human handoff | Frozen per governance — not in scope this phase |

---

## Parking lot (not yet ready to ideate)

- KB article compile workflow: step 9G triggered kb-autopopulate.yml on 2026-08-13 — if #403 resolved, this should auto-recover. Monitor before adding new recovery logic.
- Response_score.py ai_usage_guard: file path unknown — needs a grep session before a concrete proposal can be written.
- Nightly review consecutive-commit-zero alert: 3 days without production commits is unusual but may reflect weekend cadence. Monitor another cycle.

---

## Completed (last 5 runs)

| Run | Winner | Status |
|-----|--------|--------|
| 099 | Step 9F KB staleness alert | IMPLEMENTED (in nightly SKILL.md) |
| 100 | Step 9G self-healing KB trigger | IMPLEMENTED (in nightly SKILL.md) |
| 101 | Step 9G KB autopopulate direct-impl | IMPLEMENTED (PR open) |
| 102 | Create route-security-guard-audit SKILL.md | CARRY-FORWARD |
| 103 | Add brain-connector age gate to Step 9C | RECOMMENDED (this run) |
