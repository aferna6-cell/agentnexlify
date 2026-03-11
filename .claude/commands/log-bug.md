I just fixed a bug. Help me document it for future reference.

Ask me:
1. What was the symptom?
2. What was the root cause?
3. What files did you change?
4. What was the fix?

Then append a new entry to docs/dev-knowledge/bug-patterns.md in this format:

### [Short description]
**Date:** [today's date]
**Symptom:** [what was observed]
**Root Cause:** [the technical problem]
**Files Changed:** [list]
**Fix:** [what was done]
**Prevention:** [how to avoid in future]

If the bug involved a schema mismatch, also append to docs/dev-knowledge/schema-log.md.
If the bug reveals a recurring pattern, suggest creating a new skill for it.
