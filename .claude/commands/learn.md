---
description: Extract reusable patterns from the current session and save as learned knowledge.
---

# Learn — Pattern Extraction

Analyze the current session and extract patterns worth remembering.

## What to Extract

1. **Error resolutions** — non-obvious fixes (add to `docs/dev-knowledge/bug-patterns.md`)
2. **Schema discoveries** — column names, FK relationships, constraints that surprised us
3. **Workarounds** — library quirks, API limitations, version-specific fixes
4. **Architecture decisions** — why we chose X over Y (add to `docs/dev-knowledge/architecture-decisions.md`)
5. **Debugging techniques** — tool combinations or diagnostic patterns that worked

## Process

1. Review the session for extractable patterns
2. Classify each pattern (error/schema/workaround/architecture/debugging)
3. Save to the appropriate knowledge file:
   - Bug patterns → `docs/dev-knowledge/bug-patterns.md`
   - Schema changes → `docs/dev-knowledge/schema-log.md`
   - Architecture decisions → `docs/dev-knowledge/architecture-decisions.md`
   - Memory-worthy items → auto-memory system
4. Report what was saved

## Rules

- Only extract patterns that would save time in a future session
- Skip one-time fixes and simple typos
- Include the "why" not just the "what"
- Update existing entries rather than duplicating
