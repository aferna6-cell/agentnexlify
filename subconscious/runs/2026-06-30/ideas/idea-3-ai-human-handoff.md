# Idea 3: AI-to-Human Handoff v1 (Scoped via os_outbound_mirror.py)

**Run:** 73 | **Date:** 2026-06-30 | **Origin:** Run 4 (2026-04-16), 75+ days pending

## One-line
Implement scoped AI-to-Human Handoff using `os_outbound_mirror.py` to reduce scope from "all industries" to ~1 day of work.

## Background
- Listed in `docs/dev-knowledge/customer-gaps.md` as Critical gap across ALL 7 industries.
- Run 4 (April 16, 2026) — first recommendation. 75+ days with zero movement.
- `active_directions` in governance.json: entry at `"source_run": 4` still `pending_approval`.
- `rejected_paths` includes "full AI-to-human handoff in one PR" — too broad, failed 7 times.
- Previous scoping attempt via `os_outbound_mirror.py`: mirrors outbound messages to human inbox without touching widget flow. ~1 day effort vs full handoff (3+ days).

## Evidence
- `docs/dev-knowledge/customer-gaps.md`: "Critical" + "Medium" effort. Affects salon, plumber, dental, HVAC, law firm, real estate, contractor verticals.
- GoHighLevel "AI Employee" directly addresses handoff — our #1 competitive gap.
- No new evidence since last 7 recommendations. Same gap, same scope question.
- `os_outbound_mirror.py` approach still undocumented in codebase — not shipped, not started.

## What it involves (scoped)
1. `os_outbound_mirror.py` — service that listens to AI message stream and CC's human operator email.
2. New endpoint: `POST /api/handoff/enable` — tenant opts in; stores email + threshold (e.g., "forward after 3 unanswered intents").
3. Frontend toggle: 1 settings toggle + email input. No new page required.

## Effort
- M (Medium) — 1–2 days scoped. Full handoff: 3–4 days.
- Files: `backend/services/os_outbound_mirror.py` (new) + `backend/routers/handoff.py` (new) + `frontend/src/pages/Settings.jsx` (modify).
- Migration: new `handoff_configs` table.

## Risk
- Migration required → schema-guardian gate before backend-dev.
- Touches Settings page (shared with multiple features).
- 7 previous failed recommendations suggest scope/priority mismatch, not technical risk.

## Why this loses to Idea 1
- M-effort vs S-effort.
- 7 failed recommendations: pattern suggests owner not ready to commit session time.
- No new evidence since last recommendation.
- Moratorium: adding M-effort item with migration to queue while 4-6 already waiting.

## Recommendation
Parking lot. Re-evaluate run 75 with concrete owner commitment signal. Do not re-recommend without new evidence of readiness.
