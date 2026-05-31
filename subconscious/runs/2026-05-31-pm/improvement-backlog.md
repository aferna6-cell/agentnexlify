# Improvement Backlog — 2026-05-31-pm (Run 43)

## Active

- **Extend AUTONOMOUS-EXECUTABLE scope to pre-commit bash additions in nightly-commit-review SKILL.md** — completes run 42 Step 2; enables Item A (check_project_invariants pre-commit, 29-day pending) to execute autonomously tonight. [Run 43 winner]

## Parking Lot (survived debate but not chosen)

- **Invoke /god-class-splitter on email_sequences.py** — 1255L → email_crud + email_enrollment + email_processor. All tooling ready. Do GH #181 first (~15 min). ~2h human session. [Run 41 active_direction stands]
- **AI-to-Human Handoff v1 via Agent OS** — os_outbound_mirror.py ready, ~1 day scope. Day 45 Critical gap. Do not re-recommend as winner until moratorium exits. [Run 38 active_direction stands]
- **Add Item D to AUTONOMOUS-EXECUTABLE** — lead-qualifier-eval.yml (additive CI YAML). Premature until Item A confirms tonight. Target run 44. [Run 14 active_direction stands as subsumed_in_sprint]
- **GH #107 Zapier API key plan_status enforcement** — ROI 2.5, security fix, 31 days open. Route via issue-to-pr-loop. Not a subconscious winner candidate while moratorium active.

## Rejected This Run

- **email_sequences.py split as run 43 winner** — Valid idea, weakened: higher activation barrier (2h human, GH #181 prerequisite) vs. Idea 1 (5 min SKILL.md edit, autonomous tonight). Run 41 active_direction stands.
- **AI-to-Human Handoff as run 43 winner** — No new evidence since run 38. Mechanism lacks forcing function for ~1 day M-effort commitment. Do not re-recommend as winner until moratorium exits.

## Questions for Next Run (Run 44)

1. Did nightly 2026-06-01 implement Item A (check_project_invariants in pre-commit)? Check: `grep -n "check_project_invariants" scripts/hooks/pre-commit`
2. Was Item A implemented tonight as a result of the SKILL.md extension, or did it again fail? If failed: root cause — did nightly update the SKILL.md with the new bullet first, then implement Item A? Two-step issue?
3. If Item A confirmed: is Item D (lead-qualifier-eval.yml) ready to add to AUTONOMOUS-EXECUTABLE block?
4. Was GH #181 billing fix applied (billing.py 15000 + 25000)?
5. Moratorium status: any items completed, pending count change?
