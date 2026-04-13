# Claude Code Best-Practice Audit — AgentNexLiFy

Audit date: 2026-04-13
Reference: https://github.com/shanraisshan/claude-code-best-practice (v2.1.101)

Six-module compliance review. Gaps closed inline. Items flagged WONT-FIX retained for cause.

## Module 1 — Subagents (`.claude/agents/`)

18 agents. Spec-compliant frontmatter (`name`, `description`, `tools`, `model`, `maxTurns`, `skills`, `mcpServers`).

Compliance: **OK**.

Optional enhancements deferred:
- `color` field per agent (visual only, not functional)
- `permissionMode` per agent (currently inherits session default)

Coverage map:
- Architecture / planning: `architect`, `opus-advisor`
- Execution: `sonnet-executor`, `backend-dev`, `frontend-dev`, `widget-specialist`
- Quality: `code-reviewer`, `qa-tester`, `security-reviewer`, `performance-optimizer`, `vertical-checker`
- Specialized: `schema-guardian`, `devops`, `refactor-cleaner`, `tdd-guide`
- GAN loop: `gan-planner`, `gan-generator`, `gan-evaluator`

## Module 2 — Commands (`.claude/commands/`)

19 commands. 14 were missing YAML frontmatter — fixed this audit.

Added `description` + optional `argument-hint` + `model` to:
`checkpoint, delegate, deploy-check, deploy, evening, fix-bug, health-check, log-bug, morning, new-feature, recover, refactor, script, summary`.

Model routing applied per `.claude/rules/model-routing.md`:
- Haiku: `checkpoint, log-bug, summary`
- Sonnet: `deploy-check, deploy, evening, fix-bug, health-check, morning, recover, refactor, script`
- Opus: `delegate, new-feature`

Compliance: **OK**.

## Module 3 — Skills (`.claude/skills/`)

49 skills. 32 used underscored frontmatter fields (`user_invocable`, `allowed_tools`, `argument_hint`, `disable_model_invocation`) — Claude Code spec uses hyphenated form.

Bulk-renamed to hyphenated per `best-practice/claude-skills.md`:
- `user_invocable` → `user-invocable`
- `allowed_tools` → `allowed-tools`
- `argument_hint` → `argument-hint`
- `disable_model_invocation` → `disable-model-invocation`

Non-spec fields (`version`, `origin`, `triggers`) retained — additive metadata, no harm.

Compliance: **OK**.

## Module 4 — Hooks

Hook scripts live in `scripts/claude-hooks/`. Best-practice convention is `.claude/hooks/` but Claude Code reads whatever path `settings.json` points at — non-functional naming preference only.

Hook coverage:
- `PreToolUse` (Bash, Edit|Write, mcp__github__create_pull_request, WebFetch|WebSearch)
- `PostToolUse` (Write|Edit, Agent|Task)
- `PostToolUseFailure`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `TaskCompleted`, `WorktreeRemove`, `Stop`, `FileChanged`

Includes Boris Cherny patterns:
- PostToolUse auto-format / auto-lint (last 10% for CI)
- Stop hook nudges via `confidence-gate.sh`
- Permission review routed to Haiku for `git push` (`pre-commit-review` agent hook)
- Security scan routed to Haiku on auth/payment file edits

Compliance: **OK**. Directory name non-standard but functionally equivalent.

## Module 5 — MCP Servers (`.mcp.json` + `settings.json`)

5 project-scoped servers: `supabase`, `financial-datasets`, `aidesigner`, `context7`, `playwright`.

Best-practice daily-five: Context7, Playwright, Claude in Chrome, DeepWiki, Excalidraw.
- Context7: **present**
- Playwright: **present** (also via plugin)
- Chrome DevTools: **present** via `chrome-devtools-mcp` plugin
- DeepWiki: **present** via `deepwiki` tools
- Excalidraw: **absent** (low priority — architecture diagrams infrequent)

`enableAllProjectMcpServers: true` set for this trusted project; global setting keeps `false` per security rule so untrusted cloned repos require explicit approval.

Secrets via `${VAR}` expansion — no keys in git.

Compliance: **OK**.

## Module 6 — Settings + Memory (`.claude/settings.json`, `CLAUDE.md`, `.claude/rules/`)

### settings.json
- `permissions.allow/deny/ask` — layered per Trail-of-Bits guide
- `sandbox.enabled: true` with bubblewrap verified
- `effortLevel: "high"`, `autoCompactWindow: 400000`
- `enabledPlugins` — 36 plugins scoped, collision-prone ones disabled (see `.claude/rules/plugins.md`)

Compliance: **OK**.

### CLAUDE.md
120 lines — under the <200 line BP target. Delegates domain detail to `.claude/rules/*.md`. Uses `@path`-style imports via referenced rule files.

Compliance: **OK**.

### Rules (`.claude/rules/`)
23 rule files split by domain (api-conventions, python-fastapi, schema-discipline, widget-rules, security-rules, caveman-mode, ultrathink, no-assumptions, model-routing, parallel-approaches, kb-first, prompt-library, etc).

Matches Boris Cherny monorepo split pattern.

Compliance: **OK**.

## Summary

| Module | Pre-audit | Post-audit |
|--------|-----------|-----------|
| Subagents | OK | OK |
| Commands | 14/19 missing frontmatter | OK |
| Skills | 32/49 underscored fields | OK |
| Hooks | Non-standard path | OK (path is config, not spec) |
| MCP | OK | OK |
| Settings + Memory | OK | OK |

## Boris Cherny tips checklist

- [x] Plan mode for non-trivial work (`.claude/rules/ultrathink.md`)
- [x] `.claude/rules/` split (23 files)
- [x] Slash commands for inner-loop workflows (19 project commands)
- [x] Feature-specific subagents + skills (18 agents, 49 skills)
- [x] Auto-format PostToolUse hook (`scripts/claude-hooks/auto-format.sh`)
- [x] Stop hook nudge (`scripts/claude-hooks/confidence-gate.sh`)
- [x] Permission review routed to Haiku (pre-push git hook)
- [x] `/permissions` wildcard patterns (not `--dangerously-skip-permissions`)
- [x] `/sandbox` enabled
- [x] Small-PR + pre-push gate convention (git hooks enforce checks; squash-merge is repo setting)
- [x] `/code-review` plugin enabled
- [x] Cross-model workflow (Codex via `codex:codex-rescue`)
- [x] Daily `/morning` + `/evening` routines
- [x] Memory system at `~/.claude/projects/.../memory/`

## Round 2 follow-ups (closed 2026-04-13)

- Commands: rewrote descriptions as triggers ("Use when X") per Thariq tip
- Agents: added `color:` to all 18 (purple=planning, blue=backend, red=critical, cyan=frontend/widget, green=execution, yellow=review, orange=ops, pink=eval)
- Hooks: evaluated `.claude/hooks` symlink → removed after review (settings.json still points at `scripts/claude-hooks/*.sh`, so the symlink was non-functional dead weight and created Windows portability risk)
- Project-custom frontmatter (`version`, `origin`, `triggers`) retained — required by `scripts/claude-hooks/validate-skill.sh` hook
- JSON validation: `jq -e .` passes on `.claude/settings.json` + `.mcp.json`

## Open follow-ups

- Add Excalidraw MCP when architecture-diagram need arises
- Runtime verify after session restart that trigger-style descriptions improve auto-invocation (no measurable gain yet — next session)
