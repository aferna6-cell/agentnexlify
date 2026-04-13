---
description: Save the current session state to disk so it survives compaction.
model: haiku
---

Save the current session state to disk so it survives compaction.

Read the current conversation context and create/update `.claude/agent-comms/checkpoint.md` with:

## Session Checkpoint — [current date and time]

### What We're Working On
[Summarize the current task]

### Decisions Made So Far
[List key decisions from this session]

### Files Modified
[List all files that have been created, edited, or deleted]

### Current Status
[Where are we in the task? What's done, what's remaining?]

### Agent Outputs
[Summarize any agent output files that exist in .claude/agent-comms/]

### Key Context That Must Not Be Lost
[Any critical details, error messages, or constraints that would be expensive to rediscover]

### Next Steps
[What should happen next when this checkpoint is read back]

---

Also update docs/daily-logs/current-tasks.md with the current task status.

After saving, tell me: "Checkpoint saved. If context gets compacted, tell me to read the checkpoint and I'll pick up where I left off."
