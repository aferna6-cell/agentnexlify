# AI Development System

The repository has a multi-layered AI-assisted development system that makes development safer and captures institutional knowledge automatically.

## System Layers

### Layer 1: Brain + Skills
- **CLAUDE.md** — Auto-read by Claude Code every session. Contains project rules, schema info, critical patterns.
- **Skills** — Reusable workflows in `.claude/skills/` and `.codex/skills/` that Claude Code follows for specific task types.
- **Knowledge Base** — Persistent docs in `docs/dev-knowledge/` that accumulate bug patterns, schema history, and architecture decisions.

### Layer 2: Manual Commands
- **Slash commands** in `.claude/commands/` that developers invoke on demand.

### Layer 3: Automated Enforcement
- **Git hooks** — pre-commit and pre-push checks that run automatically.
- **GitHub Actions** — PR/push checks and auto bug logging. No workflow is scheduled any more, and the estate has been dark since 2026-07-20 (GH #500); `scripts/ci_local.sh` stands in as the real gate.
- **Claude Code hooks** — pre-edit and post-edit checks that run during Claude Code sessions.

---

## CLAUDE.md

The brain file at the repo root. Claude Code reads it automatically at the start of every session. Contains:
- Critical rules (schema conventions, dangerous imports, widget sync)
- Tech stack and architecture overview
- Database schema table built from actual migration files
- Workflows for common tasks (new endpoint, new page, migration)
- Links to skills, automation, and knowledge base

## Skills

### Claude Code Skills (`.claude/skills/`)

| Skill | When to Use |
|-------|-------------|
| **schema-guard** | BEFORE any database query, migration, or Pydantic model change. Prevents schema mismatch bugs. |
| **debug-api** | When diagnosing 422s, 500s, CORS failures, silent data loss, webhook issues. |
| **feature-build** | When building any new feature. Ensures schema safety and consistent patterns. |
| **widget-test** | When testing, debugging, or modifying the chat widget. |

### Repository-Native Skills (`.codex/skills/`)

| Skill | Purpose |
|-------|---------|
| **agentnexlify-surface-selector** | Choose the right surface/subsystem before editing |
| **agentnexlify-schema-guard** | Protect live schema conventions and data invariants |
| **agentnexlify-widget-integrity** | Keep widget contract and mirrored assets consistent |
| **agentnexlify-runtime-constraints** | Account for multi-worker runtime behavior |

## Slash Commands

| Command | What It Does |
|---------|-------------|
| `/health-check` | Scans for schema mismatches, dead imports, bare excepts, dangerous imports, unregistered routes, widget sync issues. Saves report. |
| `/log-bug` | Interactive bug documentation. Asks for symptom/cause/fix, appends to bug-patterns.md and schema-log.md. |
| `/deploy-check` | Pre-deploy validation: secrets scan, build check, migration safety, schema consistency, CORS check, widget sync. |

## Automated Checks

### Pre-Commit Hook (`scripts/hooks/pre-commit`)
Runs before every `git commit`. **Blocks** on:
- Hardcoded secrets (API keys, tokens)
- `from __future__ import annotations` in router files
- .env files being committed

**Warns** on:
- Bare `except: pass` blocks
- Duplicate migration numbers

### Pre-Push Hook (`scripts/hooks/pre-push`)
Runs before every `git push`. **Blocks** on:
- Frontend build failure
- Backend import failure
- `from __future__ import annotations` in routers
- .env not in .gitignore

**Warns** on:
- Schema mismatches (tenant_id in leads code, lead_stage usage)
- Widget file sync issues

### Claude Code Hooks (`.claude/settings.json`)
Run automatically during Claude Code sessions:

**Pre-edit** (`scripts/claude-hooks/pre-edit-check.sh`):
- Blocks .env file edits
- Warns when editing existing migrations (should be immutable)
- Notes when editing main.py (CORS/router registration)

**Post-edit** (`scripts/claude-hooks/post-edit-check.sh`):
- Detects `from __future__ import annotations` in router files
- Flags bare except blocks
- Detects hardcoded API keys
- Warns on tenant_id usage in leads-related code
- Reminds to update schema-log.md after migration edits

### Health Check (`.github/workflows/health-check.yml`)
Manual-only (`workflow_dispatch`) — the 6 AM UTC cron was removed; see the note
on the workflow's `on:` block and
`planning/decisions/2026-08-24-actions-replacement-substrate.md`. Checks:
- Dangerous imports in routers
- Silent error handling (bare excepts)
- Hardcoded secrets
- .gitignore completeness
- Schema mismatches
- Widget file sync
- Migration numbering

Auto-creates a GitHub issue if any CRITICAL findings.

### PR Validation (`.github/workflows/pr-check.yml`)
Runs on every PR to main. **Blocks merge** on:
- Dangerous imports
- Hardcoded secrets
- .env files in PR
- Frontend build failure
- Duplicate migration numbers

**Warns** on:
- Bare except blocks
- Schema mismatches
- Widget sync issues

### Auto Bug Logger (`.github/workflows/auto-log-bug.yml`)
Runs on push to main. When commit message matches fix/bugfix/hotfix/patch patterns:
- Auto-appends entry to `docs/dev-knowledge/bug-patterns.md`
- Commits the update automatically

### AI Auto-Improve (`.github/workflows/ai-auto-improve.yml`)
Runs daily. One conservative improvement pass:
- Refreshes skill registry
- Analyzes task memory for patterns
- Scans for schema risks, duplicate code, naming inconsistencies
- Writes report to `docs/ai-auto-improve-report.md`

## Knowledge Base

### `docs/dev-knowledge/bug-patterns.md`
Every bug that's been found and fixed. Auto-updated by the bug logging Action. Add details with `/log-bug`.

### `docs/dev-knowledge/schema-log.md`
Complete migration history built from actual SQL files. Documents every schema change and known gotchas.

### `docs/dev-knowledge/architecture-decisions.md`
Why key technical choices were made. Prevents accidentally undoing intentional decisions.

## How to Install Hooks

After cloning the repo:
```bash
bash scripts/install-hooks.sh
```

This copies pre-commit and pre-push hooks to `.git/hooks/`. To bypass in an emergency: `git commit --no-verify` or `git push --no-verify`.

## How to Add New Skills

1. Create directory: `.claude/skills/<skill-name>/`
2. Create `SKILL.md` with frontmatter (name, description) and workflow steps
3. Reference it in CLAUDE.md under the Skills section

## How to Add New Commands

1. Create `.claude/commands/<command-name>.md`
2. Write the prompt that Claude Code should follow when the command is invoked
3. Use with `/command-name` in Claude Code

## The Autonomous Development Runtime

The repository also contains a self-improving autonomous development layer:

- **ai/** — Skill engine, memory, pattern extraction, auto-improve
- **skills/** — Generated skills workspace with index
- **.codex/skills/** — Repository-native skills

### How It Works
- `ai/skill_registry.py` indexes repo skills plus generated skills into `skills/index.json`
- `ai/skill_resolver.py` resolves task descriptions (repo skills → generated → external → new)
- `ai/task_memory.py` stores task records, bug patterns, architecture patterns, refactor patterns
- `ai/auto_improve.py` performs one safe improvement pass per run

### Commands
```bash
# Rebuild skill index
python3 -m ai.skill_registry rebuild

# Resolve skills for a task
python3 -m ai.skill_engine prepare "fix widget API drift"

# Record a completed task
python3 -m ai.skill_engine complete "fix widget API drift" \
  --skills-used agentnexlify-widget-integrity,agentnexlify-schema-guard \
  --files-modified widget/agentnexlify-widget.js \
  --fixes "mirrored widget files" --outcome success

# Run autonomous improvement pass
python3 -m ai.auto_improve --create-skills --write-report docs/ai-auto-improve-report.md --refresh-docs
```

## The Key Insight

The system improves because each layer catches things the others miss:

1. **Claude Code hooks** catch issues during development (before the file is even saved)
2. **Pre-commit hooks** catch issues before they enter git history
3. **Pre-push hooks** catch issues before they reach the remote
4. **PR checks** catch issues before they merge to main
5. **Daily health checks** catch issues that slip through everything else
6. **Auto bug logging** captures institutional knowledge without manual effort
7. **AI auto-improve** identifies systemic patterns across the whole codebase

No single check is perfect, but together they form a defense-in-depth system that gets smarter over time as more bugs are documented and more patterns are recognized.

<!-- ai-auto-improve:start -->
Last auto-improve scan found 17 schema risks, 3 duplicate-code groups, and 0 newly generated skills.
<!-- ai-auto-improve:end -->
