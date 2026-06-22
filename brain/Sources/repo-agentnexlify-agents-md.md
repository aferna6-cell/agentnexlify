---
type: source
source_id: repo-agentnexlify-agents-md
origin: local-repo
path: /home/user/agentnexlify/AGENTS.md
accessed: 2026-06-22
sensitivity: normal
tags: [source]
---

# Source: agentnexlify/AGENTS.md

## What this is
Agent/Codex operating contract for the repo — implementation discipline + invariants for
autonomous agents.

## What it proves
- Implementation discipline: smallest concrete change; no speculative abstraction, fallbacks,
  or catch-all try/except without a proven failure mode.
- Reinforces invariants: no `from __future__ import annotations` in FastAPI; migration workflow.
- Anthropic treated as canonical runtime AI authority for Managed Agents.
