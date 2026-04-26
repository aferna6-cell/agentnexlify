# One Task = One Chat

## Rule
Single chat session → single task. Mixing unrelated tasks in one conversation → up to 39% perf drop per Anthropic research.

## Why
- Context poisoning — old task decisions leak into new task reasoning
- Topic drift — model blends domains (backend auth concerns bleed into frontend styling)
- Memory corruption — CLAUDE.md rules get diluted by irrelevant earlier tool results
- Cache invalidation — long unrelated context forces re-read of prefix every turn
- Benchmark degradation — Anthropic-reported 39% perf drop on mixed-task sessions

## When to split to new chat
- Pivoting to unrelated domain (frontend → backend, widget → migrations, code → marketing)
- New feature after finishing previous feature (not iteration)
- Context window >60% full and work changing focus
- Message count >75 with task switch
- Switching tenant, client, or environment
- Debugging → implementing (different mindsets)

## When NOT to split
- Iterative work on same task (expected — keep context)
- Direct follow-up questions on last response
- Clarification rounds before execution
- Review/QA of code written this session
- Short pivots (<5 messages)
- Multi-file changes serving one feature

## How to split cleanly
1. Run `/checkpoint` to save session state to disk (in `.claude/commands/checkpoint.md`)
2. Run `/summary` if you want a git-activity summary for handoff
3. Start new chat
4. Run `/recover` to restore context from checkpoint
5. Reference plan file or spec in new chat's first message

## 15-message summary rule (existing)
Every 15 user prompts, `scripts/claude-hooks/message-counter.sh` forces a handoff summary. That's the within-session discipline. This rule (one-task-one-chat) is the between-session discipline.

## Anti-patterns
- Mega-chats covering 4+ unrelated features
- Debugging session that drifts into refactor
- "While we're here, also…" additive scope creep
- Keeping a chat alive across days for convenience (context decays)

## Enforcement
Self-discipline + `/checkpoint` + `/recover` commands. No hook enforcement — context-aware judgment needed.

## Cross-refs
- `.claude/rules/user-rules.md` Rule 3 — 15-msg summary
- `.claude/commands/checkpoint.md`
- `.claude/commands/recover.md`
- `.claude/commands/summary.md`

## Session hygiene moves (added 2026-04-26)
Five within-session moves alongside the between-session split rule above. Source: SolarXpander cost-optimization writeup, Thariq "Lessons from Building Claude Code".

1. **`/compact` at 50%** — don't wait for auto-compact at 80%. Compact early; auto-compact pushes you over and warms a fresh prefix anyway.
2. **`/clear` between unrelated work** — new session, fresh prefix; same as the between-session rule but mid-day cadence.
3. **`/rewind` when a turn went sideways** — cheaper than re-prompting around the bad context.
4. **Subagents for anything that doesn't need parent reasoning** — see `model-routing.md` spawn discipline.
5. **Lock tools + model at session start** — adding/removing MCP, tools, or `/model` swap mid-session invalidates the cached prefix and forces a full re-read. Project pin `claude-version-pin.md` already covers this.

## Cache hygiene rules
- Don't add MCP servers mid-session
- Don't `/model` mid-session (project default `opus` in `~/.claude/settings.json`)
- `/effort` per-prompt is safe — does not invalidate prefix (`effort-per-prompt.md`)
- 5-min cache TTL refreshes free on hit; long sessions with steady tool use stay warm indefinitely if the prefix doesn't change

## Source
Anthropic research on context window hygiene; community replication across Twitter/Reddit 2026-Q1. Session-hygiene additions: SolarXpander writeup (2026-04-26).
