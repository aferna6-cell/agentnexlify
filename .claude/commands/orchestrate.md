---
description: Decompose a multi-domain task into a dependency DAG and dispatch agents in waves. Use for work touching 3+ domains.
argument-hint: [task description]
model: opus
---

Run the coordinator skill. Read `.claude/skills/coordinator/SKILL.md` first — it owns the DAG rules, and `references/decomposition-patterns.md` holds the six DAG templates.

Task: `$ARGUMENTS`

## Steps

1. Decompose the task. Which domains are touched — schema, backend, frontend, widget, infra?
2. Build the dependency DAG. schema-guardian first when the database is touched. qa-tester always last.
3. Publish the plan (summary, numbered DAG with blockers, execution waves) to the shared GitHub issue before dispatching anything.
4. Dispatch each wave in a single turn — spawn the wave's agents concurrently, max 4 at once. Never dispatch a task whose blockers have not completed.
5. On a FAIL: pause dependents, diagnose, re-dispatch, resume.
6. After every wave: read the handoffs, update the issue plan, check the next wave's blockers.
7. Completion gate: run qa-tester on the combined result. Complete only on PASS or WARNINGS-only.

For cross-provider work, `docs/TEAM_OPERATING_CONTRACT.md` is authoritative — each agent runs `python3 scripts/teamctl.py preflight --issue <number> --agent <name>` and claims a non-overlapping lane before editing. `.claude/agent-comms/` is ephemeral same-session scratch, not durable team state.

Single-domain task, or scope still unclear? Skip the DAG and say so.
