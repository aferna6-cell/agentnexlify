---
source: docs.claude.com/en/docs/claude-code/memory
fetched_at: 2026-04-22
via: agent-browser
category: ai-llm
topic: Claude Code configuration, path-scoped rules, CLAUDE.md optimization
---

# Claude Code — CLAUDE.md, Rules, and Auto-Memory (Official Docs)

Captured from Anthropic's official Claude Code docs while verifying a community-circulated config guide. Several claims turned out to be real + official.

## CLAUDE.md

### Size target (official, not community folklore)

> "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence."

Auto-loaded into full context regardless of length — only MEMORY.md has the 200-line truncation.

### Load order
- Walks directory tree UP from CWD, concatenating every CLAUDE.md + CLAUDE.local.md found
- Subdirectory CLAUDE.md files load on-demand when Claude reads files in those dirs
- CLAUDE.local.md appended after CLAUDE.md → personal overrides win locally
- All files concatenated, no override semantics (like PATH, not like shell variables)

### What belongs in CLAUDE.md

> "Treat CLAUDE.md as the place you write down what you'd otherwise re-explain. Add to it when: Claude makes the same mistake a second time / A code review catches something Claude should have known / You type the same correction into chat that you typed last session / A new teammate would need the same context."

Keep to facts Claude should hold in EVERY session. Multi-step procedures → skill. Subtree-specific rules → `.claude/rules/` with `paths:`.

### Imports

Supports `@path/to/file` syntax up to 5-hop recursion. Absolute and relative paths. First import triggers approval dialog.

### Comments

Block-level HTML comments (`<!-- ... -->`) stripped before context injection. Use for maintainer notes without burning tokens. Preserved inside code blocks.

## `.claude/rules/` — Path-Scoped Rules

### The feature (verified real)

```yaml
---
paths:
  - "src/api/**/*.ts"
---

# API rules body
```

Rules with `paths:` load only when Claude reads matching files. Rules without `paths:` load unconditionally at session start.

### Glob patterns

| Pattern | Matches |
|---------|---------|
| `**/*.ts` | All TypeScript files in any directory |
| `src/**/*` | Everything under `src/` |
| `*.md` | Markdown at project root only |
| `src/components/*.tsx` | Specific directory |

Multiple patterns + brace expansion:
```yaml
paths:
  - "src/**/*.{ts,tsx}"
  - "lib/**/*.ts"
  - "tests/**/*.test.ts"
```

### Load semantics

- Rules load into context every session or when matching files are opened
- Trigger on file READ by Claude, not on every tool use
- Task-specific content should be in skills (load on explicit invoke) instead of rules

### Symlinks

`.claude/rules/` supports symlinks. Share rules across projects:
```bash
ln -s ~/shared-claude-rules .claude/rules/shared
ln -s ~/company-standards/security.md .claude/rules/security.md
```
Circular symlinks detected + handled.

### User-level rules

`~/.claude/rules/*.md` apply to every project. Load BEFORE project rules — project rules win on conflict.

## Managed Policy CLAUDE.md (organization-wide)

Enforced by IT/MDM, cannot be excluded by individual settings:
- macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`
- Linux/WSL: `/etc/claude-code/CLAUDE.md`
- Windows: `C:\Program Files\ClaudeCode\CLAUDE.md`

Different from managed settings:
- Managed settings = technical enforcement (block tools, commands, paths)
- Managed CLAUDE.md = behavioral guidance (style, compliance reminders)

## `claudeMdExcludes` setting

Skip CLAUDE.md files from other teams in monorepos:
```json
{
  "claudeMdExcludes": [
    "**/monorepo/CLAUDE.md",
    "/home/user/monorepo/other-team/.claude/rules/**"
  ]
}
```
Add to `.claude/settings.local.json` for local-only exclusion. Merges across layers. Managed policy CLAUDE.md files cannot be excluded.

## Auto-Memory

- Requires Claude Code v2.1.59+
- On by default; toggle via `/memory` or `autoMemoryEnabled: false`
- Storage: `~/.claude/projects/<project>/memory/`
- Project key derived from git repo → all worktrees share one memory dir
- MEMORY.md index loaded every session (first 200 lines or 25KB)
- Topic files (`debugging.md` etc.) load on-demand via Read tool
- Machine-local — not shared across machines or cloud envs
- Redirect via `autoMemoryDirectory` in user or local settings (NOT project settings — prevents shared project from redirecting to sensitive paths)

## Troubleshooting

- **Claude ignoring CLAUDE.md**: content delivered as user message after system prompt, not as system prompt itself. Not strict compliance. Debug via `/memory` to verify load, remove vague/conflicting instructions, use `InstructionsLoaded` hook to log exactly what loaded.
- **CLAUDE.md too large**: >200 lines reduces adherence. Split into `.claude/rules/` with `paths:` or move to skills.
- **Instructions lost after `/compact`**: project-root CLAUDE.md survives, re-injected from disk. Nested CLAUDE.md only reloads on next subtree read.

## `--append-system-prompt` CLI flag

For instructions that MUST be at system-prompt level (stricter adherence than CLAUDE.md):
```bash
claude --append-system-prompt "Always use pnpm, never npm."
```
Must pass every invocation — scripts/automation only.

## `InstructionsLoaded` hook

Hook event (not currently wired in this repo) logs exactly which instruction files loaded, when, and why. Useful for debugging path-scoped rules or lazy-loaded subdirectory files.

## Applied findings for AgentNexLiFy

1. **CLAUDE.md line 5** says `≤500 lines` — updated to `≤200 lines` matching official guidance
2. **Path-scoped rules already wired** on all 7 domain rules (python-fastapi, widget-rules, schema-discipline, frontend-patterns, api-conventions, testing-standards, security-rules) — audit complete
3. **Behavioral rules correctly unscoped** — caveman-mode, ultrathink, user-rules, etc. stay always-load
4. **New rule file** `.claude/rules/path-scoped-rules.md` as author guide for future additions
5. **`InstructionsLoaded` hook** could be added for debugging if path-scoping ever misbehaves
6. **`claudeMdExcludes`** not relevant — no monorepo pollution
7. **Symlink pattern** interesting for future cross-project rule sharing if we spin a second repo

## Process note

This capture was triggered by `fill-instructions-before-guessing.md` — community-circulated guide claimed `paths:` frontmatter existed as native feature; I marked it UNVERIFIED and checked primary source before recommending migration work. Feature turned out real, but my initial audit claim ("we're not using paths:") was also wrong — we ARE, on all 7 domain rules. Both verifications cost <5min and prevented wrong-direction work.

## Source

https://docs.claude.com/en/docs/claude-code/memory (Anthropic, live as of 2026-04-22, fetched via agent-browser)
