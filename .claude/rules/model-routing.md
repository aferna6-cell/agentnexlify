---
paths:
  - "**/*"
---

# Model Routing — Right Model for Right Task

## Models

| Model | ID | Use for |
|-------|-----|---------|
| **Haiku** | `claude-haiku-4-5-20251001` | grammar, formatting, lookups, bullet lists, renames, translations, quick classification, hook scanners |
| **Sonnet** | `claude-sonnet-4-6` | code, debug, API calls, multi-file edits, most Agent executions, default implementation |
| **Opus** | `claude-opus-4-6` | planning, architecture, security design, critical review, ambiguous decomposition |

## Pattern for non-trivial tasks
**Opus plans → Sonnet executes → Haiku cleans up.**

## Never
- Never Opus for mechanical work (rename, format, lookup)
- Never Haiku for architecture or security design
- Never default to Opus when Sonnet fits — Opus is expensive

## Hook agent model delegation
- Security scanner on auth/payment file edit → Haiku
- Pre-push code review → Haiku
- Plan/architecture review → Opus
- Bulk refactor execution → Sonnet

## Cost awareness
Opus is 5x Sonnet, 15x Haiku per token. Every Opus call should justify the depth.
