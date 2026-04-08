---
paths:
  - "**/*"
---

# GitNexus — Code Intelligence

Project indexed as **agentnexlify** (7900 symbols, 18223 relationships, 300 execution flows).

> If any tool warns the index is stale, run `npx gitnexus analyze` first.

## Before Editing Any Symbol
- MUST run `gitnexus_impact({target: "symbolName", direction: "upstream"})` — report blast radius
- MUST warn user if impact returns HIGH or CRITICAL risk
- MUST run `gitnexus_detect_changes()` before committing

## When Debugging
1. `gitnexus_query({query: "<error>"})` — find related execution flows
2. `gitnexus_context({name: "<suspect function>"})` — callers, callees, processes
3. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})`

## When Refactoring
- Renaming: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first
- NEVER rename with find-and-replace — use `gitnexus_rename` which understands the call graph

## Tools Quick Reference
| Tool | Command |
|------|---------|
| Find by concept | `gitnexus_query({query: "auth validation"})` |
| Symbol 360 | `gitnexus_context({name: "validateUser"})` |
| Blast radius | `gitnexus_impact({target: "X", direction: "upstream"})` |
| Pre-commit check | `gitnexus_detect_changes({scope: "staged"})` |
| Safe rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |

## Impact Risk: d=1 WILL BREAK (must update), d=2 LIKELY AFFECTED (should test), d=3 MAY NEED TESTING

## Keeping Fresh
After commits: `npx gitnexus analyze` (add `--embeddings` if embeddings exist — check `.gitnexus/meta.json`). PostToolUse hook handles this automatically after `git commit`.

## Skill Files
| Task | Skill |
|------|-------|
| Architecture | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Impact analysis | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Debugging | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Refactoring | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
