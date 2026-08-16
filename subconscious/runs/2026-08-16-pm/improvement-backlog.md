# Run 105 — Improvement Backlog (2026-08-16-pm)

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
| 1 | Create route-security-guard-audit SKILL.md | code_health | S | IMPLEMENTED (run 105 direct escalation) | Run 102 winner → Run 105 escalation |
| 2 | Add Step 9J: orphaned-commits detector to nightly | operational | XS | AUTONOMOUS-EXECUTABLE (run 106 bonus) | Run 105 runner-up |
| 3 | scoring_config.py add block_demo_role | security | XS | PENDING-APPROVAL (GH #661 filed) | Run 104 security finding |
| 4 | appointment_briefs.py add block_demo_role | security | XS | PENDING-APPROVAL (GH #643 open 8d) | GH #643 |
| 5 | Step 9K: draft PR staleness alerter | operational | XS | RECOMMENDED (parking lot) | Run 105 idea 5 |
| 6 | Wire PR #653 draft → ready-for-review | operational | XS | BONUS-ACTION (one-off) | Run 103+104 carry |

---

## Blocked (human-action-required)

| # | Title | Blocker | Issue |
|---|-------|---------|-------|
| B1 | Resume brain connector | GitHub PAT + SUPABASE_ACCESS_TOKEN rotation needed | #394 (24d open) |
| B2 | Resume autopilot issue-to-PR loop | AUTOPILOT_GH_TOKEN expired | #399 (38d open) |
| B3 | KB autopopulate resume | ANTHROPIC_API_KEY missing in GH Actions | #403 (38d open) |
| B4 | Close GH #643 (appointment_briefs.py security) | PR #653 needs human review + merge | #643 (8d open) |
| B5 | Close GH #661 (scoring_config.py security) | Needs human review (security code) | #661 (0d open) |
| B6 | Provision INTEGRATIONS_ENC_KEY | Railway migration 176 blocked | #536 |
| B7 | Recover orphaned commits | 7 commits in detached HEAD not on origin/main | Structural finding from nightly-2026-08-16 |

---

## Frozen

| Title | Reason |
|-------|--------|
| AI-to-human handoff | Frozen per governance — not in scope this phase |
| Widget drift | FORBIDDEN from subconscious permanently (widget_drift_topic_retired: true) |

---

## Parking lot (not yet ready to ideate)

- **Step 9I paying-tenant 0-conversation alert**: Supabase MCP availability in headless nightly sessions unconfirmed. Monitor before writing the step.
- **Step 9J orphaned-commits detector**: RUNNER-UP this run. XS effort. Recommended for run 106 nightly bonus action. Evidence: 7 commits orphaned 2026-08-16.
- **Step 9K draft-PR staleness alerter**: Parked pending Step 9J. Multiple subconscious PRs >14d draft.
- **Lead Source Analytics dashboard**: Blocked on GH #399 (AUTOPILOT_GH_TOKEN). ai-ready issue exists.
- **Schedule conversation_enrichment_job.py**: Blocked on GH #399. Re-evaluate after AUTOPILOT_GH_TOKEN rotation.

---

## Completed (last 5 runs)

| Run | Winner | Status |
|-----|--------|--------|
| 100 | Step 9G KB autopopulate self-healing trigger | IMPLEMENTED (commit in nightly SKILL.md) |
| 101 | Step 9G direct escalation | IMPLEMENTED (subconscious run 101, 2026-08-06) |
| 102 | Create route-security-guard-audit SKILL.md | CARRY-FORWARD → IMPLEMENTED at run 105 |
| 103 | Add brain-connector age gate to Step 9C | IMPLEMENTED same-day (commit 60499dd) |
| 104 | Add SUPABASE_ACCESS_TOKEN to rotation schedule | IMPLEMENTED (nightly-2026-08-16, commit ddd8e77) |
| 105 | Create route-security-guard-audit SKILL.md | IMPLEMENTED (run 105 direct escalation, 2026-08-16) |
