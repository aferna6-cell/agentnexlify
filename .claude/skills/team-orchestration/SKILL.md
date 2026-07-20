---
name: team-orchestration
description: "Use this skill when a task is complex enough to benefit from delegating to multiple agents with specific roles and coordination patterns."
version: 1.0.0
origin: claude
triggers: ["team orchestration", "delegate to agents", "multi-agent task", "orchestrate agents", "full stack feature", "database change workflow"]
effort: high
---

# Team Orchestration

For Codex, Fable 5, and Kimi 3, first read `docs/TEAM_OPERATING_CONTRACT.md`. One GitHub issue is the durable shared task hub. Run `python3 scripts/teamctl.py preflight --issue <number> --agent <name>`, claim non-overlapping lanes, and keep all durable coordination in structured issue comments.

## When to Use

- Task involves both backend AND frontend work
- Task involves database changes (always route through schema-guardian first)
- Task is complex enough that breaking it into specialist subtasks would produce better results
- You want to validate changes (always involve qa-tester after implementation)

## When NOT to Use

- Simple questions about the codebase (just read the file yourself)
- Single-file changes with no cross-cutting concerns
- Tasks that are clearly within one domain with no validation needed
- When the developer explicitly says to do something directly

## Agent Team

| Agent | Role | Tools | Best For |
|-------|------|-------|----------|
| schema-guardian | DB schema validator | Read-only | Pre-validate any DB work |
| backend-dev | FastAPI developer | Read/Write | API endpoints, business logic |
| frontend-dev | React developer | Read/Write | Dashboard pages, components |
| widget-specialist | Widget expert | Read/Write | Chat widget, embedding |
| qa-tester | Quality assurance | Read + Bash | Validation, bug checking |
| devops | Infrastructure | Read/Write | Deploy prep, CI/CD |

## Delegation Patterns

### Pattern 1: New Feature (Full Stack)
1. schema-guardian → validate/create schema (parallel with step 2 if no DB changes)
2. backend-dev → build API (uses schema-guardian output)
3. frontend-dev → build UI (can run in parallel with backend if API contract is clear)
4. qa-tester → validate everything
5. devops → deploy prep (if needed)

### Pattern 2: Bug Fix
1. qa-tester → reproduce and diagnose (identify which area)
2. [relevant specialist] → implement fix
3. qa-tester → verify fix, check for regressions

### Pattern 3: Database Change
1. schema-guardian → audit current schema, design migration
2. backend-dev → update Pydantic models and queries
3. frontend-dev → update any affected UI (if needed)
4. qa-tester → validate entire data path

### Pattern 4: Widget Change
1. widget-specialist → implement change
2. schema-guardian → validate if data flow changed
3. qa-tester → cross-origin testing checklist

### Pattern 5: Pre-Deploy
Run in parallel:
- qa-tester → full validation
- devops → deploy checklist
Compile results → report to developer

## Communication Protocol

1. **Task prompt**: Include the shared issue, claimed lane, dependencies, file paths, and acceptance criteria.
2. **Durable events**: Use `scripts/teamctl.py update|handoff|review|proof`; never rely on one provider's private context.
3. **Passing context**: Handoff comments name the recipient, changed files, evidence, and remaining risk. The receiver explicitly claims the lane.
4. **Conflict resolution**: Executable evidence wins, then `brain/`, ADRs, issue acceptance criteria, and a two-of-three peer decision.
5. **Local proof**: Run the repository gates locally and commit with `[skip ci]`; never dispatch GitHub Actions for team work.
6. **Scratch files**: `.claude/agent-comms/` remains allowed only for ephemeral same-session specialist output and is cleaned after completion.

## When NOT to Delegate

- Simple questions about the codebase (just read the file yourself)
- Single-file changes with no cross-cutting concerns
- Tasks that are clearly within one domain with no validation needed
- When the developer explicitly says to do something directly
