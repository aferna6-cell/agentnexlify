---
type: source
source_id: docs-production-runbook
origin: local-repo
path: /home/user/agentnexlify/docs/production-runbook.md
accessed: 2026-06-22
sensitivity: normal
tags: [source]
---

# Source: docs/production-runbook.md

## What this is
Production deploy + incident runbook.

## What it proves
- Deploy order: backend tests (Python 3.12 `.venv312`) → frontend tests/build → migrations
  first → backend → frontend after `/healthz` → watch logs 15 min.
