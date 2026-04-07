---
description: Answer a quick side question without losing current task context. Read-only — never modifies files.
---

# Aside

Answer `$ARGUMENTS` without losing the current task.

## Process

1. **Freeze**: Note what task is active and what step is in progress
2. **Answer**: Concise, direct answer. Read files if needed (read-only)
3. **Resume**: Continue the active task from the exact point it was paused

## Format

```
ASIDE: [restate question briefly]

[Answer — lead with the answer, not reasoning]

— Back to task: [one-line description of what was being done]
```

## Rules

- Never modify files during an aside
- If the answer reveals a problem with the current task, flag it and ask before continuing
- If no question provided, ask what the user wants to know
- Keep answers short — offer to go deeper after the current task
