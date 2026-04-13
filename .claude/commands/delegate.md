---
description: Plan and delegate a complex task across the specialist agent team.
model: opus
---

You have a team of specialized agents available. Before starting any complex task, create a delegation plan.

## Step 1: Analyze the Task

Determine what type of work this involves:
- Database/schema changes? → schema-guardian agent
- Backend API work? → backend-dev agent
- Frontend/dashboard work? → frontend-dev agent
- Chat widget work? → widget-specialist agent
- Testing/validation? → qa-tester agent
- Deployment/infrastructure? → devops agent

## Step 2: Create the Plan

Write a delegation plan to `.claude/agent-comms/orchestrator-plan.md` with:
- Task summary
- Which agents are needed
- Order of operations (what can run in parallel vs. what depends on prior results)
- What context each agent needs

## Step 3: Execute

For independent tasks: spawn agents in parallel.
For dependent tasks: run sequentially, passing prior agent output in the delegation prompt.

Always include in each agent's delegation prompt:
- The specific subtask to complete
- Relevant file paths
- Any decisions or constraints from prior agents
- Where to write output (`.claude/agent-comms/{agent-name}-output.md`)

## Step 4: Compile Results

After all agents complete:
1. Read all output files from `.claude/agent-comms/`
2. Resolve any conflicts between agent recommendations
3. Present the unified result to the developer
4. Clean up: delete all files in `.claude/agent-comms/` except README.md and .gitkeep

## Agent Team

| Agent | Specialty | When to Use |
|-------|-----------|-------------|
| schema-guardian | Database schema, migrations, validation | Any task touching the database |
| backend-dev | FastAPI routes, Pydantic models, Supabase queries | Backend feature work, API changes |
| frontend-dev | React/Vite components, dashboard UI | Frontend feature work, UI changes |
| widget-specialist | Chat widget, embedding, cross-origin | Widget changes, customer-facing chat |
| qa-tester | Testing, validation, bug detection | After any code changes, before deploy |
| devops | CI/CD, deployment, infrastructure | Deploy prep, GitHub Actions, hosting |

## Rules

- If only one agent is needed, delegate directly — no need for a plan file
- If the task is simple enough for you to handle directly, just do it
- Always run schema-guardian BEFORE backend-dev when database changes are involved
- Always run qa-tester AFTER implementation agents finish
- Include file paths and error messages in delegation prompts — agents start with fresh context
