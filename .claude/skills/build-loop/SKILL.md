---
name: build-loop
description: "Autonomous infinite development loop. Constantly builds features, tests, debugs, refactors, and evolves the codebase. Reads backlog, picks highest-priority work, executes it, commits, and repeats. Run /build-loop to start."
user_invocable: true
---

# Autonomous Build Loop

You are now an autonomous development agent running in a continuous loop. You build features, write tests, fix bugs, generate content, and optimize — then repeat forever.

## STARTUP

1. Read `.claude/agent-comms/loop-prompt.md` for the full autonomous development instructions
2. Read `.claude/agent-comms/backlog.md` for the work queue
3. Read `.claude/agent-comms/loop-log.md` for previous cycle history (avoid redoing work)
4. Read `.claude/agent-comms/checkpoint.md` if it exists (restore state from previous session)
5. Read `docs/daily-logs/current-tasks.md` for additional context on priorities

## THE CYCLE

Each cycle follows this exact sequence:

### STEP 1: ANALYZE
- Determine which level of the work hierarchy to operate at (Features → Bugs → Tests → Simulation → Research → Content → Optimization → System Evolution)
- Pick 3-5 tasks from the highest available level
- Plan knowledge deposits for this cycle

### STEP 2: PLAN
Write your plan to `.claude/agent-comms/loop-plan.md`:
- Which hierarchy level
- Which tasks from the backlog
- Expected knowledge deposits
- Agent delegation plan (use team-orchestration skill if multi-domain)

### STEP 3: BUILD
- Use relevant skills (schema-guard, ai-feature-pattern, feature-build, debug-api, etc.)
- Delegate to agents when appropriate (schema-guardian → backend-dev + frontend-dev → qa-tester)
- Make changes, test as you go

### STEP 4: REFACTOR (mandatory every cycle)
Based on cycle number mod 5:
- 0: Dead code sweep
- 1: Error handling hardening
- 2: Consistency pass
- 3: Documentation debt
- 4: Performance & security scan

### STEP 5: TEST
- Run `cd frontend && npm run build` to verify frontend
- Run `python3 -m pytest tests/ -q --timeout=30` to verify tests
- Fix any failures before proceeding

### STEP 6: BUSINESS LOGIC GATE
Pass all 7 gates from the loop prompt before committing:
1. Critical path smoke test
2. Diff review
3. Scope check (max 10 files per cycle)
4. Rollback safety
5. Schema integrity
6. Model ID verification
7. No silent behavior changes

### STEP 7: COMMIT & PUSH
- Group changes into logical commits
- Include cycle number in commit messages
- Push to remote after each commit
- Follow the commit message format from the loop prompt

### STEP 8: CHECKPOINT
- Update `.claude/agent-comms/loop-log.md` with cycle summary
- Write `.claude/agent-comms/checkpoint.md` with current state
- Update `docs/daily-logs/current-tasks.md` with completed/new tasks
- Update backlog.md (mark completed, add discovered work)

### STEP 9: NEXT CYCLE
Announce completion and immediately start the next cycle:
"Cycle [N] complete. Built: [what]. Cleaned: [what]. Knowledge: [what]. Starting cycle [N+1]."

**Then go back to STEP 1. The loop never ends.**

## IMPORTANT RULES

- **Always read the backlog fresh at the start of each cycle** — the user may have added tasks
- **Never skip the business logic gate** — when in doubt, revert
- **Push after every commit** — triggers auto-deploy
- **Maximum 10 files per cycle** — if touching more, break it up
- **Every cycle must deposit knowledge** — update docs/dev-knowledge/
- **Create skills/agents/hooks when patterns repeat 3+ times**
- **If context is getting heavy, run /checkpoint then /compact**

## CONTEXT MANAGEMENT

The loop runs within a single Claude Code session. When context gets heavy:
1. Run `/checkpoint` to save state
2. The session will auto-compact when needed
3. After compaction, re-read checkpoint.md and loop-log.md to restore state
4. If the session ends, the user can restart with `/build-loop` and you'll pick up from the checkpoint

For truly infinite operation, use the external shell loop:
```bash
bash scripts/continuous-loop.sh /home/aidan/agentnexlify
```
This restarts Claude sessions automatically when they end.
