# Improvement Backlog — 2026-05-19-pm (Run 26)

## Active

- Invoke /moratorium-sprint in this session: execute 4 S-effort items (A: pre-commit Check 10, B: widget sync guard, C: nightly SKILL.md escalation protocol, D: CI eval workflow), open draft PR, pending 11→7 when merged.

---

## Parking Lot (survived debate but not chosen)

- **nightly-commit-review auto-invoke trigger** (WEAKENED) — Add `## Auto-Trigger Protocol` to .claude/skills/nightly-commit-review/SKILL.md: when `moratorium_active=true` AND `days_without_production_commits > 7`, auto-invoke moratorium-sprint. Valid but requires sprint to execute first so skill is validated. Promote in run 27 if sprint still unexecuted.

- **dep-batch-merge** (KILLED as winner, valid bonus) — Merge PRs #163, #164, #102, #103 (~5 min). Independent of moratorium. Do alongside sprint or anytime.

- **pre-commit-guard-add skill** (not debated, parking lot) — Create .claude/skills/pre-commit-guard-add/SKILL.md. Saves 15 min per new guard. Promote to post-moratorium winner queue.

- **governance-state-sync skill** (not debated, parking lot) — Automate governance.json reconciliation (5 min per subconscious run). Promote to post-moratorium winner queue.

- **Zapier plan_status enforcement** (GH #107, parking lot carry-over) — HIGH security. `backend/services/zapier_auth.py::_get_api_key_client` misses plan_status check. Promote to first post-moratorium non-customer-value winner.

- **email sequences N+1 fix** (GH #112, parking lot carry-over) — M-effort. list_enrollments: 1 DB call per enrollment. Promote when email adoption grows or moratorium exits.

---

## Rejected This Run

- **Invoke /moratorium-sprint as the primary standalone recommendation without escalation path** — The governance mandate fires. Even if sprint is recommended, the auto-trigger escalation must be logged in governance.json as fallback. Run cannot end without honoring the mandate.

---

## Questions for Next Run

1. Was /moratorium-sprint invoked? Which of the 4 items completed? Did the draft PR open?
2. If not invoked: did nightly-commit-review auto-trigger fire (per run 26 governance escalation)? Is the trigger wired?
3. Have safe dep PRs (#163, #164, #102, #103) been merged?
4. Is moratorium-sprint skill validated (verified correct execution) or just created?
5. Post-sprint: is pending now ≤ 7? What's the new critical path to ≤ 2?

---

## Post-Moratorium Queue (for when pending ≤ 2)

1. AI-to-Human Handoff v1 (run 4, Critical, all 7 industries, day 33) — ~1.5 days
2. Zapier plan_status enforcement (GH #107, High security) — M-effort
3. pre-commit-guard-add skill — workflow improvement
4. dep-batch-merge bonus — if not done during moratorium
5. email N+1 fix (GH #112) — depends on email adoption
