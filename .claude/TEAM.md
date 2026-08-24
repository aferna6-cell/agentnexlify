# AgentNexLiFy AI Team Configuration

Tailored agent team built for the AgentNexLiFy stack: FastAPI + React/Vite + Supabase + Anthropic API.

## MCP Servers (5 active)

| Server | Purpose | Key Tools |
|--------|---------|-----------|
| **Context7** | Live library docs — never use stale training data | `resolve-library-id`, `get-library-docs` |
| **Playwright** | Browser E2E testing and automation | `navigate`, `click`, `screenshot`, `expect` |
| **DeepWiki** | GitHub repo understanding for competitor analysis | `ask`, `search` |
| **Sequential Thinking** | Chain-of-thought for complex reasoning | `sequentialthinking` |
| **Memory** | Persistent knowledge graph across sessions | `create_entities`, `search_nodes` |

Plus project-scoped: Supabase, Railway, Vercel, Gmail, Google Calendar.

## Agent Team (16 core agents; 60 total in `.claude/agents/`)

### Tier 1 — Always Engaged
| Agent | Model | When to Use |
|-------|-------|-------------|
| `schema-guardian` | sonnet | Before ANY database query, migration, or Pydantic model |
| `backend-dev` | sonnet | FastAPI routes, services, business logic, Supabase queries |
| `frontend-dev` | sonnet | React pages, components, API integration, dark theme |
| `qa-tester` | sonnet | After code changes — validate, catch regressions |

### Tier 2 — On Demand
| Agent | Model | When to Use |
|-------|-------|-------------|
| `widget-specialist` | sonnet | Chat widget behavior, CORS, embed script, cross-origin |
| `code-reviewer` | sonnet | Post-implementation quality check |
| `security-reviewer` | sonnet | Auth, payments, webhooks, tenant isolation |
| `devops` | sonnet | Deploy prep, Railway/Vercel config, CI/CD |

### Tier 3 — Architecture
| Agent | Model | When to Use |
|-------|-------|-------------|
| `architect` | opus | System design, scalability, technical decisions |
| `performance-optimizer` | sonnet | N+1 queries, bundle size, render performance |
| `refactor-cleaner` | sonnet | Dead code removal, consolidation |

### Tier 4 — GAN Harness
| Agent | Model | When to Use |
|-------|-------|-------------|
| `gan-planner` | opus | Expand feature spec into full product plan |
| `gan-generator` | opus | Implement features per spec |
| `gan-evaluator` | opus | Test live app via Playwright, score against rubric |

### Tier 5 — Cross-Cutting
| Agent | Model | When to Use |
|-------|-------|-------------|
| `vertical-checker` | sonnet | Final gate: schema, RLS, performance, widget sync, build |
| `tdd-guide` | sonnet | Enforce test-first methodology |

## Delegation Order

```
Feature work:  schema-guardian → backend-dev + frontend-dev (parallel) → qa-tester → code-reviewer
Bug fixes:     schema-guardian → backend-dev or frontend-dev → qa-tester
Pre-deploy:    qa-tester + devops + security-reviewer (parallel) → vertical-checker
Architecture:  architect (opus) → plan review → backend-dev + frontend-dev (execute)
E2E testing:   gan-evaluator (uses Playwright MCP)
```

## Command Quick Reference

| Command | What |
|---------|------|
| `/new-feature` | Full pipeline: schema → backend → frontend → QA → commit |
| `/fix-bug` | Diagnose → fix → verify → document |
| `/deploy` | QA + devops parallel → final gate |
| `/e2e` | Playwright E2E tests for specific flows |
| `/docs <lib>` | Live docs via Context7 (not training data) |
| `/aside <q>` | Quick question without losing task context |
| `/learn` | Extract reusable patterns from session |
| `/compound` | 5-agent pipeline: brainstorm → plan → execute → review → vertical |
| `/orchestrate` | Parallel worktrees, each running compound pipeline |
| `/delegate` | Plan agent delegation before starting complex tasks |

## Proven Workflows (from ECC best practices)

### 1. Plan-First Development
```
/plan → confirm → /tdd → implement → /code-review → /verify → /deploy
```

### 2. Research-Before-Edit
```
/docs <library> → /aside "is this the right pattern?" → implement
```

### 3. Continuous Learning
```
After fixing non-trivial bugs: /learn → saves to bug-patterns.md
After architecture decisions: /learn → saves to architecture-decisions.md
```

### 4. Context Management
```
Before long tasks: /checkpoint
After compaction: /recover
Heavy context: /aside for side questions (preserves main task)
```

### 5. Multi-Agent Feature Build
```
/new-feature "description"
  → schema-guardian checks schema
  → backend-dev + frontend-dev in parallel
  → qa-tester validates
  → code-reviewer audits
  → /deploy-check before merge
```
