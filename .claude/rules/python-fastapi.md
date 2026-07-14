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
Valid model IDs (July 2026): `claude-sonnet-5`, `claude-opus-4-8`, `claude-haiku-4-5-20251001`. Legacy-but-still-valid: `claude-sonnet-4-6`, `claude-opus-4-7` (many background call sites still use these; fine to keep). NEVER use a model ID not on this list. See `.claude/rules/model-routing.md` for the canonical routing table.

## Model Selection for AI Features
- Widget chat responses: `claude-sonnet-5` (near-Opus reasoning at Sonnet cost, 2026-06-30), `stream=True`. Resolved via `resolve_string_setting("widget_chat_model", MODEL)` — per-tenant DB override wins. NOTE: Sonnet 5's tokenizer maps text to ~1.0-1.35x more tokens than 4.6; `ai_usage_guard.PLAN_BASELINE_TOKENS` still needs re-baselining against real Sonnet-5 usage.
- Complex tasks (documents, quotes, analysis): `claude-opus-4-8` or an `AdvisorExecutorRunner` with Opus planning and Sonnet/Haiku execution
- Opus/Sonnet Messages API calls: omit `temperature`, `top_p`, and `top_k`; use `thinking: {"type": "adaptive"}` plus `output_config.effort` when deeper reasoning is needed
- Streaming thinking: set `thinking.display: "omitted"` unless the UI explicitly renders summarized thinking
