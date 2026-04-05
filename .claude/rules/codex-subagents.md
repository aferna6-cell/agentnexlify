---
paths:
  - "**/*"
---

# Codex-First Subagent Rule

When spawning subagents for implementation, diagnosis, or research work, prefer the `codex:codex-rescue` skill over native Agent tool spawns.

## How to Apply

Instead of:
```
Agent(subagent_type="backend-dev", prompt="Fix the auth endpoint...")
```

Do:
```
Skill("codex:rescue", args="Fix the auth endpoint in backend/routers/auth.py — the JWT validation is rejecting valid tokens because...")
```

## When to Use Codex Rescue

- Bug fixes and diagnosis
- Implementation tasks (backend, frontend, widget)
- Research and code exploration
- Refactoring work
- Any task you would normally delegate to a subagent

## When to Use Native Agents Instead

- Tasks that require Claude-specific tools (Supabase MCP, Railway MCP, memory system)
- Tasks that need to call other skills or MCP servers
- Multi-turn interactive work that needs Claude's full tool suite
- Schema-guardian checks (needs Supabase MCP access)

## Prompt Quality

Use the `codex:gpt-5-4-prompting` skill mentally when composing rescue prompts:
- Be specific about file paths and line numbers
- Include the "why" not just the "what"
- Mention constraints (don't use `from __future__ import annotations`, use `client_id` not `tenant_id`, etc.)
- Add `--write` for implementation, omit for read-only research
