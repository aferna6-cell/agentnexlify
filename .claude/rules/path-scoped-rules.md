# Path-Scoped Rules — Author Guide

Anthropic `paths:` frontmatter feature. Confirmed real via docs.claude.com/en/docs/claude-code/memory on 2026-04-22.

## Rule

New rule files in `.claude/rules/` MUST decide explicitly: always-load (no `paths:`) or path-scoped (with `paths:`). Default to path-scoped when the rule only applies to a specific subtree.

## How it works

- Rules without `paths:` frontmatter → load at session start, every session, forever
- Rules with `paths:` frontmatter → load only when Claude reads a file matching any listed glob
- Path-scoped rules trigger on file READ, not on every tool use — parsimonious with context
- Works recursively — `.claude/rules/backend/*.md` all discovered

## Current state (audit 2026-04-22)

Path-scoped already (verified):
- `python-fastapi.md` → `backend/**/*.py`
- `widget-rules.md` → `widget/**/*` + `frontend/public/widget/**/*`
- `schema-discipline.md` → `backend/**/*.py` + `migrations/**/*.sql`
- `frontend-patterns.md` → `frontend/**/*.{jsx,js,css}`
- `api-conventions.md` → `backend/routers/**/*.py`
- `testing-standards.md` → `**/*.test.*` + `**/*.spec.*`
- `security-rules.md` → specific auth/billing router files

Always-load (no `paths:`, intentional):
- All behavioral rules (caveman-mode, model-routing, no-assumptions, ultrathink, etc.)
- All Opus 4.7 feature rules (self-verification, ultrareview, task-budgets, etc.)
- claude-code-security.md (universal threat model)
- user-rules.md (plan-first, ask-when-unsure)
- fill-instructions-before-guessing.md

## When to add `paths:`

Add when:
- Rule's content only applies to one language/framework (Python → `backend/**/*.py`)
- Rule guards a specific subtree (widget → `widget/**/*`)
- Rule is about a file type (tests → `**/*.test.*`)
- Rule references file paths that don't exist in other subtrees

Don't add when:
- Rule is about HOW Claude thinks (caveman, ultrathink, user-rules)
- Rule is about workflow orchestration (plan-first, 15-msg summary)
- Rule is universal security (never commit secrets)
- Rule is about model selection or API shape (opus-4-7, model-routing)

## Glob pattern reference

| Pattern | Matches |
|---------|---------|
| `**/*.py` | All Python files anywhere |
| `backend/**/*` | Everything under backend/ |
| `*.md` | Markdown only at project root |
| `backend/**/*.{py,sql}` | Brace expansion for multi-extension |
| `backend/routers/**/*.py` | Python in specific subdir tree |

Multiple patterns combine OR-wise:
```yaml
---
paths:
  - "backend/**/*.py"
  - "migrations/**/*.sql"
---
```

## Author checklist for new rules

Before committing a new `.claude/rules/<name>.md`:
1. Decide: always-load or path-scoped?
2. If path-scoped: verify globs match intended files via `find . -path "<glob>"`
3. If behavioral/universal: no `paths:` block
4. Keep body ≤150 lines (same adherence logic as CLAUDE.md 200-line target applies)
5. Cross-ref related rules at bottom

## Debugging

- `/memory` in session lists all loaded CLAUDE.md + rules
- `InstructionsLoaded` hook (not currently wired) logs exactly which rules fire — add if path-scoping ever misbehaves
- `claudeMdExcludes` setting in settings.json can skip rules by glob (monorepo only — not relevant for us)

## Anti-patterns

- Never add `paths:` to a behavioral rule — breaks always-apply contract
- Never use `paths: ["**/*"]` — equivalent to no `paths:`, just don't add frontmatter
- Never path-scope security rules to "files where security matters" — attackers work everywhere, always-load security-rules is fine
- Never assume `paths:` means file EDIT — it means file READ by Claude

## Cross-refs

- Official docs: https://docs.claude.com/en/docs/claude-code/memory
- `knowledge-base/raw/ai-llm/claude-code-path-scoped-rules-2026-04-22.md` — docs capture
- `.claude/rules/fill-instructions-before-guessing.md` — why I now audit before claiming features are missing
- `CLAUDE.md` §"Rule files index" — full list of rules by category
