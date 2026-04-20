---
name: agentnexlify-task-loader
description: "Dispatch AgentNexLiFy tasks to the right repo-local skill and verification path before editing."
version: 1.0.0
origin: codex
triggers: ["agentnexlify task loader", "dispatch this task", "which skill should I load", "what should I check first", "load the right skill"]
---

# AgentNexLiFy Task Loader

Use this as the first pass for ambiguous repo work. Load the narrowest skill that matches the task surface, then follow the doc/check path for that surface.

## Route map
- DB, schema, backend data, migrations, Supabase queries -> load `agentnexlify-schema-guard`; read `backend/CONTEXT.md` and the relevant router plus matching `migrations/`.
- Widget, embed, business-page embed path, widget config -> load `agentnexlify-widget-integrity`; check `widget/agentnexlify-widget.js`, `frontend/public/widget/agentnexlify-widget.js`, and `backend/routers/widget.py`.
- Automation, rate limits, quotas, worker-local state, durable runtime behavior -> load `agentnexlify-runtime-constraints`; inspect `backend/main.py` and any cache/loop/sender code involved.
- Ambiguous repo task or unclear surface -> load `agentnexlify-surface-selector` first, then the selected surface skill.
- Frontend UI, dashboard pages, public app rendering -> read `frontend/CONTEXT.md`, then use the relevant frontend/build checks for the changed page or component.
- AI runtime, customer-facing prompt assembly, model behavior, tool routing -> read `CLAUDE.md`, `docs/AI_ARCHITECTURE_AUDIT.md`, and `docs/dev-knowledge/architecture-decisions.md` before editing the call site.
- General verification -> prefer root-level checks when they exist, starting with `npm run check:quick` and `npm run check:full`; otherwise run the surface-specific tests and builds.

## Working rule
- If one skill is enough, stop there.
- If the task crosses surfaces, load the primary surface skill plus the invariant-enforcing skill that matches the shared risk.
