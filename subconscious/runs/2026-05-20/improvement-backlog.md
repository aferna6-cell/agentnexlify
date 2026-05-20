# Improvement Backlog — 2026-05-20 (Run 26)

## Active

- **Invoke /moratorium-sprint** — execute 3 remaining S-effort items (A: check_project_invariants pre-commit ~5 min, B: widget sync guard ~15 min, D: CI eval workflow ~20 min). Item C done autonomously today. Sprint ~40 min total. Skill exists (7985fbb). One command.

## Parking Lot (survived debate, not chosen this run)

- **pre-commit-guard-add skill** — WEAKENED this run (moratorium active). Skill discovery 2026-05-18 ranked #2 after moratorium-sprint. 15-20 min saved per new guard, ~1-2/month cadence. Promote to run 27 first candidate when moratorium exits.
- **AI-to-Human Handoff v1 GH issue** — Critical gap, 35 days pending, all 7 industries. M-effort. Post-moratorium first free-choice candidate.
- **Merge safe dep PRs** (#102, #103, #163, #164) — independent bonus action, safe any time. ~5 min.
- **Zapier plan_status enforcement** — security bug GH #107, ROI 2.5. Post-moratorium.
- **Email sequences N+1 fix** — GH #112, ROI 2.3. Post-moratorium.
- **Authorize nightly autonomous execution of Items A+B** — KILLED this run (parallel execution conflict with sprint PR model). Revisit only if sprint PR model abandoned.

## Rejected This Run

- **Authorize nightly review for Items A+B** — KILLED. Parallel execution conflict with sprint PR model creates merge-conflict risk. Nightly review's organic autonomous scope (skill-file additions) is working correctly; extending it to hook modifications requires guardrails that don't exist. Wrong mechanism.

## Governance Correction Applied This Run

- **Run 19 (Moratorium Escalation Protocol)** — status `pending_approval` → `implemented`. Done by nightly review 2026-05-20 (commit 2ce31b2). Second autonomous implementation in 2 consecutive days.

## Questions for Next Run

- Was /moratorium-sprint invoked? If yes: pending 9→6, begin moratorium exit path. If no: escalate — run 27 winner should be triggering the sprint from nightly review as scheduled autonomous execution.
- Did the nightly review escalation comment fire on GH #169? (Expected yes — Moratorium Escalation Protocol now in SKILL.md.)
- Are safe dep PRs (#102, #103, #163, #164) merged? If still open after 25+ days, flag as abandoned/stale.
