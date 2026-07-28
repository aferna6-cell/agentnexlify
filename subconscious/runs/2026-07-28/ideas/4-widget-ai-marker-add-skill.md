# Idea 4 — Create `widget-ai-marker-add` SKILL.md

**Category:** Workflow efficiency  
**Evidence strength:** MEDIUM — 2 occurrences (HANDOFF_REQUESTED historical, SHOW_BOOKING_PANEL e9b4972 #573 2026-07-23)  
**Execution channel:** nightly commit-review (SKILL.md file creation proven)

## What

Create `.claude/skills/widget-ai-marker-add/SKILL.md` encoding the 7-step pattern for adding a new AI-triggered UI action marker to the widget chat.

## Evidence

From `docs/skill-discovery/2026-07-27.md`:

Two occurrences with identical structure:
1. HANDOFF_REQUESTED (historical) — inline detection, return signal `{"handoff": true}`
2. SHOW_BOOKING_PANEL (e9b4972, #573, 2026-07-23) — extracted detection module, tenant gate, return signal `{"show_booking": true}`

The second improved on the first (extracted module, tenant gate). Pattern is converging toward a stable shape.

## Steps the skill encodes

1. Add marker string to system prompt in `backend/services/booking_prompt.py` — specific WHEN condition
2. Create `backend/routers/widget_chat_<action>.py` with `detect_<marker>()` — strip marker, check tenant flag, return bool
3. Wire into `backend/routers/widget_chat.py` step 9-series — import, call, suppress if tenant flag off, add to response JSON, strip from rendered text
4. Add optional bool field to `backend/models/schemas.py` with `= None` default
5. In widget JS: add `if (data.<signal>) { <action>() }` check in response handler
6. **Byte-identical sync**: copy to `frontend/public/widget/` AND `landing-page-v2/widget/`. Run `scripts/check_project_invariants.py`.
7. Write test: marker in text → signal true + marker stripped; tenant flag off → signal false; marker absent → both false

## Why it matters

Steps 6 (byte-identical sync) and the strip-before-render invariant are the most error-prone and most likely to be skipped under time pressure. The second occurrence explicitly shows what happens without the skill: the first marker (HANDOFF_REQUESTED) had no extraction module and no tenant gate — both were improvements the developer added when building SHOW_BOOKING_PANEL, which implies they discovered the pattern themselves.

Saves 20-35 min per new marker. Estimated frequency: ~1/month.

## Ranking vs Idea 1

Lower frequency than `feature-docs-trio` (1×/month vs 3×/2weeks). Higher per-occurrence risk (byte-identical sync failure breaks widget on tenant sites — revenue impact). Worth creating but lower urgency.
