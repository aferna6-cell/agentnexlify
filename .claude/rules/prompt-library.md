---
paths:
  - "**/*"
---

# Prompt Library — Use It First

## Rule
BEFORE starting any task:
1. Read `PROMPTLIBRARY.md` at repo root
2. Find matching prompt by category: Research / Debug / Write / Review / Build / Test / Reason / Summarize
3. Follow its `Context needed` and `Steps` exactly
4. After completion, update the prompt with what you learned
5. If no prompt exists, create one

## Treat prompts as versioned software components
- Improve every time you use one
- Reusable, tested, documented
- Version bump on changes (v1.0.0 → v1.1.0)
- Broken prompt = bug, fix immediately

## Format
```
### [CATEGORY] Prompt Name (vX.Y.Z)
**When to use:** [triggers]
**Context needed:** [files, commands to run first]
**Steps:**
1. ...
2. ...
```

## Pointer
`/home/aidan/agentnexlify/PROMPTLIBRARY.md`

## Why this exists
Prompts that worked → save them. Prompts that failed → fix them. Compounding quality every session.
