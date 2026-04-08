---
name: team-orchestration
description: "Use this skill when a task is complex enough to benefit from delegating to multiple agents with specific roles and coordination patterns."
version: 1.0.0
origin: claude
triggers: ["team orchestration", "delegate to agents", "multi-agent task", "orchestrate agents", "full stack feature", "database change workflow"]
effort: high
---

# Team Orchestration

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

1. **Task prompt**: When delegating, include ALL context the agent needs (file paths, error messages, prior agent output, specific instructions)
2. **Output files**: Each agent writes to `.claude/agent-comms/{agent-name}-output.md`
3. **Passing context**: When one agent depends on another's output, read the output file and include relevant parts in the next agent's delegation prompt
4. **Conflict resolution**: If agents disagree (e.g., backend-dev wants a column name that schema-guardian says is wrong), schema-guardian wins on schema questions, architecture-decisions.md wins on architecture questions
5. **Cleanup**: After task completion, delete all files in `.claude/agent-comms/` except README.md and .gitkeep

## When NOT to Delegate

- Simple questions about the codebase (just read the file yourself)
- Single-file changes with no cross-cutting concerns
- Tasks that are clearly within one domain with no validation needed
- When the developer explicitly says to do something directly
