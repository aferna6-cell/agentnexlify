---
name: worktree-orchestrator
description: Manage 4-8 parallel git worktrees, each running its own compound engineering pipeline for high quality at high throughput. Use when user says 'worktree', 'parallel worktrees', 'orchestrate worktrees', 'run in parallel', 'compound engineering', 'worktree setup', or asks about worktree orchestrator.
version: 1.0.0
origin: claude
user-invocable: true
allowed-tools:
- Read
- Write
- Edit
- Bash
- Glob
- Grep
- Agent
- TaskCreate
- TaskUpdate
- TaskList
triggers:
- worktree
- parallel worktrees
- orchestrate worktrees
- run in parallel
- compound engineering
- worktree setup
effort: high
---

# Worktree Orchestrator

Manage multiple Claude Code sessions running in parallel across isolated git worktrees. Each worktree runs its own compound engineering pipeline on a separate task. No conflicts. No shared state. Pure parallelism.

## The Multiplier Effect

```
Single session:     1 task at a time  →  1x throughput
Compound pipeline:  5 agents/task     →  higher quality per task
Worktree parallel:  4-8 worktrees     →  4-8x throughput
Combined:           compound + worktrees = high quality * high throughput
```

The skill is managing multiple AI agents in parallel without losing track. That's the next evolution of engineering.

## When to Use

- User has 2+ independent tasks to work on
- `/orchestrate` or `/parallel` command
- User says "run these in parallel", "use worktrees"
- Any batch of work where tasks don't share files
- End-to-end codebase testing (each vertical in its own worktree)

## When NOT to Use

- Tasks that modify the same files (will cause merge conflicts)
- Tasks with strict ordering dependencies
- Single task (just use compound-engineering directly)
- Quick one-off fixes

---

## Phase 1: Task Decomposition

Before creating worktrees, decompose the work into independent streams.

### Independence Test

For each pair of tasks, ask:
1. Do they modify the same files? → NOT independent
2. Does one depend on the other's output? → NOT independent
3. Do they touch the same database tables? → MAYBE independent (check if schema changes conflict)
4. Do they both modify main.py? → NOT independent (router registration conflicts)

### Task Queue Format

Write to `.claude/agent-comms/worktree-queue.md`:

```markdown
# Worktree Task Queue
## Created: {timestamp}

## Tasks
| # | Task | Branch | Status | Worktree | Dependencies |
|---|------|--------|--------|----------|-------------|
| 1 | {description} | compound/{slug} | queued | — | none |
| 2 | {description} | compound/{slug} | queued | — | none |
| 3 | {description} | compound/{slug} | queued | — | none |
| 4 | {description} | compound/{slug} | queued | — | none |

## Parallel Capacity: {N} (recommended: 4, max: 8)

## Conflict Analysis
- Tasks 1 and 2: INDEPENDENT (different files)
- Tasks 1 and 3: INDEPENDENT (different domains)
- ...
```

---

## Phase 2: Worktree Setup

### 2.1 Verify .worktrees is gitignored

```bash
# Check if .worktrees exists
ls -d .worktrees 2>/dev/null

# If not, create and gitignore
mkdir -p .worktrees
echo ".worktrees/" >> .gitignore
git add .gitignore
git commit -m "chore: add .worktrees to gitignore"
```

### 2.2 Create Worktrees

For each task in the queue:

```bash
# Create worktree with dedicated branch
git worktree add .worktrees/{task-slug} -b compound/{task-slug}

# Verify it's clean
cd .worktrees/{task-slug}
git status  # should be clean

# Install dependencies (if needed)
cd frontend && npm install 2>/dev/null
cd ..
```

### 2.3 Verify Baseline

Each worktree should start from a clean, working state:

```bash
# Frontend builds
cd .worktrees/{task-slug}/frontend && npm run build

# No pre-existing issues
cd .worktrees/{task-slug}
grep -rn "from __future__ import annotations" backend/routers/ | wc -l  # should be 0
```

### 2.4 Report Readiness

```markdown
## Worktrees Ready

| Worktree | Branch | Baseline | Status |
|----------|--------|----------|--------|
| .worktrees/task-auth | compound/task-auth | CLEAN | ready |
| .worktrees/task-billing | compound/task-billing | CLEAN | ready |
| .worktrees/task-widget | compound/task-widget | CLEAN | ready |
| .worktrees/task-analytics | compound/task-analytics | CLEAN | ready |

All {N} worktrees ready. Launch Claude Code sessions to begin.
```

---

## Phase 3: Parallel Execution

### Option A: Manual Session Management (Recommended)

Each worktree gets its own terminal/Claude Code session:

```bash
# Terminal 1
cd .worktrees/task-auth
claude  # starts Claude Code in this worktree
# → Run: /compound {task description}

# Terminal 2
cd .worktrees/task-billing
claude
# → Run: /compound {task description}

# Terminal 3
cd .worktrees/task-widget
claude
# → Run: /compound {task description}

# Terminal 4
cd .worktrees/task-analytics
claude
# → Run: /compound {task description}
```

### Option B: Agent-Based Parallel (Within Single Session)

For simpler tasks, dispatch agents in parallel from the orchestrator session:

```
[Dispatch 4 agents simultaneously, each with isolation: "worktree"]

Agent 1 (worktree): Run compound pipeline on auth task
Agent 2 (worktree): Run compound pipeline on billing task
Agent 3 (worktree): Run compound pipeline on widget task
Agent 4 (worktree): Run compound pipeline on analytics task
```

### Option C: Script-Based Orchestration

```bash
#!/bin/bash
# scripts/parallel-compound.sh

TASKS=("task-auth" "task-billing" "task-widget" "task-analytics")

for task in "${TASKS[@]}"; do
    echo "Launching compound pipeline in .worktrees/$task"
    cd ".worktrees/$task"
    claude --print "Run the compound-engineering pipeline on: $task" &
    cd -
done

echo "All ${#TASKS[@]} sessions launched. Monitor with:"
echo "  watch -n5 'for t in ${TASKS[*]}; do echo \"\$t:\"; cat .worktrees/\$t/.claude/agent-comms/compound/*/manifest.md 2>/dev/null | grep Status -A10; echo; done'"

wait
echo "All sessions complete."
```

---

## Phase 4: Progress Monitoring

### Dashboard Check

From the main repo (not a worktree), monitor all pipelines:

```bash
# Quick status of all worktrees
for wt in .worktrees/*/; do
    task=$(basename "$wt")
    manifest=$(find "$wt/.claude/agent-comms/compound/" -name "manifest.md" 2>/dev/null | head -1)
    if [ -f "$manifest" ]; then
        status=$(grep -c "\[x\]" "$manifest" 2>/dev/null || echo 0)
        echo "$task: $status/5 agents complete"
    else
        echo "$task: not started"
    fi
done
```

### Status Board Format

Update `.claude/agent-comms/worktree-queue.md` as pipelines progress:

```markdown
## Live Status
| Worktree | Agent 1 | Agent 2 | Agent 3 | Agent 4 | Agent 5 | Overall |
|----------|---------|---------|---------|---------|---------|---------|
| task-auth | DONE | DONE | IN PROG | — | — | 40% |
| task-billing | DONE | DONE | DONE | DONE | IN PROG | 80% |
| task-widget | DONE | IN PROG | — | — | — | 20% |
| task-analytics | DONE | DONE | DONE | PASS | PASS | 100% |
```

---

## Phase 5: Merge & Integration

When all worktrees complete their compound pipelines:

### 5.1 Review Each Worktree's Output

Read the coordination report from each:
```bash
for wt in .worktrees/*/; do
    task=$(basename "$wt")
    report=$(find "$wt/.claude/agent-comms/compound/" -name "coordination-report.md" 2>/dev/null | head -1)
    if [ -f "$report" ]; then
        echo "=== $task ==="
        head -30 "$report"
        echo
    fi
done
```

### 5.2 Merge Strategy

Merge worktrees back to main one at a time, in dependency order:

```bash
# Switch to main
cd /path/to/main/repo
git checkout main

# Merge each worktree branch
git merge compound/task-auth --no-ff -m "compound: auth improvements"
git merge compound/task-billing --no-ff -m "compound: billing updates"
git merge compound/task-widget --no-ff -m "compound: widget fixes"
git merge compound/task-analytics --no-ff -m "compound: analytics features"
```

### 5.3 Conflict Resolution

If merge conflicts occur:
1. Identify which files conflict
2. Resolve manually (or dispatch a focused agent)
3. Run the vertical checker on the merged result
4. Commit the resolution

### 5.4 Post-Merge Vertical Check

ALWAYS run a final vertical check after all merges:

```
Dispatch: vertical-checker agent
Scope: All changes from all worktree merges
Focus: Integration issues that only appear when branches combine
```

### 5.5 Cleanup

```bash
# Remove worktrees
for wt in .worktrees/*/; do
    task=$(basename "$wt")
    git worktree remove "$wt" --force
    git branch -d "compound/$task" 2>/dev/null
done

# Archive coordination reports
mkdir -p docs/compound-reports
cp .claude/agent-comms/compound/*/coordination-report.md docs/compound-reports/
```

---

## Capacity Guidelines

| Machine Resources | Recommended Parallel | Max Parallel |
|-------------------|---------------------|-------------|
| Low (8GB RAM, 2 cores) | 2 | 3 |
| Medium (16GB RAM, 4 cores) | 4 | 6 |
| High (32GB+ RAM, 8+ cores) | 6 | 8 |

**Rate limit awareness:** Each Claude Code session consumes API tokens. With Opus, 4 parallel sessions is the sweet spot. More than 8 risks hitting rate limits.

---

## Task Templates for Common Parallel Workloads

### Template: End-to-End Codebase Test

Decompose the codebase into verticals, one worktree each:

```
Worktree 1: Backend API audit (routers, models, endpoints)
Worktree 2: Frontend build & component health
Worktree 3: Widget sync & chat flow
Worktree 4: Schema/migration consistency
Worktree 5: Security scan
Worktree 6: Performance audit
```

### Template: Multi-Feature Sprint

One feature per worktree:

```
Worktree 1: Invoice PDF generation
Worktree 2: Email sequence builder
Worktree 3: Widget A/B testing
Worktree 4: Analytics dashboard
```

### Template: Bug Fix Batch

One bug per worktree (only if bugs are in different files):

```
Worktree 1: Fix appointment timezone bug
Worktree 2: Fix lead scoring calculation
Worktree 3: Fix widget session persistence
Worktree 4: Fix email template rendering
```

---

## Anti-Patterns

1. **Do NOT put conflicting tasks in parallel worktrees.** Two tasks modifying `main.py` = guaranteed merge conflict. Identify these upfront.

2. **Do NOT skip the post-merge vertical check.** Individual worktrees pass their checks, but integration issues only appear when branches combine.

3. **Do NOT run more worktrees than you can monitor.** 4 well-managed > 8 chaotic. Quality degrades when you lose track.

4. **Do NOT share state between worktrees.** Each worktree is isolated. If they need to communicate, the design is wrong — those tasks aren't independent.

5. **Do NOT merge to main without reviewing each worktree's coordination report.** The report tells you what changed, what was tested, and what the vertical checker found.

---

## Integration with Compound Engineering

Each worktree runs the full 5-agent compound pipeline:

```
Main Repo (Orchestrator)
  ├── .worktrees/task-1/  →  Claude Session 1  →  Brainstorm → Plan → Execute → Review → Vertical
  ├── .worktrees/task-2/  →  Claude Session 2  →  Brainstorm → Plan → Execute → Review → Vertical
  ├── .worktrees/task-3/  →  Claude Session 3  →  Brainstorm → Plan → Execute → Review → Vertical
  └── .worktrees/task-4/  →  Claude Session 4  →  Brainstorm → Plan → Execute → Review → Vertical
                                                                                    │
                                                                    All complete ◄───┘
                                                                         │
                                                                    Merge to main
                                                                         │
                                                                    Final vertical check
                                                                         │
                                                                    DONE
```

The compound pipeline handles quality per-task. The worktree orchestrator handles throughput across tasks. Together: high quality at high speed.
