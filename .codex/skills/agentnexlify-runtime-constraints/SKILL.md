---
name: agentnexlify-runtime-constraints
description: "Account for AgentNexLiFy runtime and deployment constraints. Use when editing background jobs, automation execution, rate limiting, caches, webhook delivery, SMS/email quotas, or any logic that assumes a single process or durable in-memory state."
version: 1.0.0
origin: codex
triggers: ["runtime constraints", "multi-worker", "automation loop", "rate limit", "quota"]
---

# AgentNexLiFy Runtime Constraints

The production backend is not a single-process toy app.

## When NOT to Use
- Do not use for frontend-only changes.
- Do not use for one-off scripts that don't run in the FastAPI lifespan.

## Core runtime facts
- `backend/main.py` starts the automation loop inside FastAPI lifespan.
- `backend/Dockerfile` runs Uvicorn with `--workers 4`.
- In-memory counters and caches are per worker, not global.

## Implications
- Do not treat in-memory rate limits, usage counters, analytics caches, or daily quotas as authoritative across the deployment.
- Any polling loop started in app lifespan will run once per worker unless explicitly externalized.
- `asyncio.create_task(...)` delivery patterns are best-effort and process-local.

## High-risk areas
- `backend/services/automation_engine.py`
- `backend/services/webhook_dispatcher.py`
- `backend/services/sms_rate_limiter.py`
- `backend/services/email_sender.py`
- Any new cache or quota logic added to routers or services

## Editing guidance
- Prefer database-backed or externally coordinated state for anything that must be globally correct.
- If a task only needs a local mitigation, document that it is process-local.
- When touching automation scheduling, check whether duplicate execution across workers is possible.
- When touching quotas or send limits, check whether the current logic is safe under multiple workers before extending it.
