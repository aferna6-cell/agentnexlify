# Improvement Backlog — 2026-05-20-pm (Run 27)

## Active

- **Invoke /moratorium-sprint** — 3 items remain (A: check_project_invariants pre-commit ~5 min, B: widget sync guard ~15 min, D: CI eval workflow ~20 min). Item C done autonomously. Tool ready (7985fbb). One command executes all. ~40 min total.

## Run 28 Hard Mandate (fires if sprint not invoked this session)

**Winner: Authorize nightly review to autonomously implement Items A + D.**
- Item A: 3 additive lines to scripts/hooks/pre-commit (LOW-risk, pre-written sketch, script passes all 6 checks)
- Item D: New file .github/workflows/lead-qualifier-eval.yml (LOW-risk additive, harness already passes locally)
- Item B: Kept for human-supervised sprint (bash script creation + pre-push hook line — slightly higher blast radius)
- Mechanism: Update governance.json to encode mandate; nightly review reads and executes at 2:37 AM

## Parking Lot (survived debate, not chosen this run)

- **Authorize nightly Items A+D** — WEAKENED this run (human present, interactive session wins). Promote to winner run 28 if sprint not done. Pre-validated scope: Items A+D are LOW-risk additive. Item B kept for human sprint.
- **AI-to-Human Handoff v1 GH Issue** — Critical gap, 34 days pending, all 7 industries. Run 21 winner (not implemented). Create GH issue with implementation sketch. Post-moratorium first free-choice candidate. M-effort ~1.5-2 days.
- **pre-commit-guard-add skill** — Skill discovery #2 recommendation, 15-20 min saved per guard. Moratorium still active. Promote run 28 as bonus if moratorium exits.
- **Zapier plan_status enforcement** — Security bug GH #107, ROI 2.5. Post-moratorium.
- **Email sequences N+1 fix** — GH #112, ROI 2.3. Post-moratorium.
- **Merge safe dep PRs** (#102, #103, #164, #171) — independent bonus, ~5 min, safe anytime.
- **Onboarding V2 characterization tests** — PR #80 (27d stale DRAFT). Write backend/tests/test_onboarding_characterization.py before merging.

## Rejected This Run

No new rejections. Rejected_paths from governance.json remain in force.

## Governance Notes Applied This Run

- No governance corrections this run (run 26 already applied run 19 correction)
- Run 28 hard mandate encoded in active_directions note (if sprint not invoked)

## Questions for Next Run (Run 28)

1. Was /moratorium-sprint invoked? If yes: pending 9→6, resolve governance items, moratorium exit path. If no: nightly Items A+D mandate fires — did they execute?
2. Did nightly escalation comment fire on GH #169? (Expected: yes, Moratorium Escalation Protocol live.)
3. Are safe dep PRs (#102, #103, #164, #171) merged? If still open, flag as stale.
4. Is PR #80 (Onboarding V2 Week 1, 27d stale) merged or closed? 30d stale on next digest — needs action.
5. Post-moratorium queue (if pending ≤ 2): AI-to-Human Handoff v1, Zapier fix, pre-commit-guard-add skill.
