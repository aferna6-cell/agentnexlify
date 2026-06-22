---
type: source
source_id: eng-memory-lessons-learned
origin: local-repo
path: /home/user/agentnexlify/docs/engineering-memory/lessons-learned.md
accessed: 2026-06-22
sensitivity: normal
tags: [source]
---

# Source: docs/engineering-memory/lessons-learned.md

## What this is
Distilled engineering lessons from prior build sessions.

## What it proves
- Most common bug pattern: `dict.get("key", default)` returns `None` for SQL NULL; correct
  form is `dict.get("key") or "default"` (22+ plan occurrences, 40+ business-field).
