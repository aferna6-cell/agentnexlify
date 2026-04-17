---
paths:
  - "backend/**/*.py"
---

# Python/FastAPI Rules

- NEVER use `from __future__ import annotations` in files with FastAPI route handlers — breaks Pydantic model resolution, causes 422 errors on every request. **Why:** PEP 563 deferred annotations make FastAPI treat body models as strings instead of types.
- Always use explicit Pydantic model classes for request bodies, not inline parameters
- CORS is configured in main.py — if widget stops working on external sites, check CORS first
- Production runs with 4 Uvicorn workers — in-memory state is per-process only
- Widget config + chat data uses 5-min TTL in-memory cache (per-worker) — invalidates automatically
- All new pip packages need `--break-system-packages` flag

## Claude API Model IDs
Valid model IDs (April 2026): `claude-sonnet-4-6`, `claude-opus-4-7`, `claude-haiku-4-5-20251001`. NEVER use a model ID not on this list.

## Model Selection for AI Features
- Widget chat responses: `claude-sonnet-4-6` (fast, 1M context), `stream=True`
- Complex tasks (documents, quotes, analysis): `claude-opus-4-7` or an `AdvisorExecutorRunner` with Opus 4.7 planning and Sonnet/Haiku execution
- Opus 4.7 Messages API calls: omit `temperature`, `top_p`, and `top_k`; use `thinking: {"type": "adaptive"}` plus `output_config.effort` when deeper reasoning is needed
- Streaming thinking: set `thinking.display: "omitted"` unless the UI explicitly renders summarized thinking
