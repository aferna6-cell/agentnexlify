---
type: procedure
name: "Widget Byte-Identical Sync"
tags:
  - procedure
  - widget
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Widget Byte-Identical Sync

## When to use
Any change to the [[Chat Widget]] JS.

## Steps
1. Edit `widget/agentnexlify-widget.js`.
2. Sync byte-identical to all mirrors: `python scripts/sync_widget_assets.py`
   (mirrors: `frontend/public/widget/`, `landing-page-v2/widget/`).
3. Verify with `--check` (CI enforces equality).
4. Test the cross-origin embed.

## Why
Mismatched copies break embeds on tenant sites — a critical invariant.

## Related
- [[Chat Widget]] · [[AgentNexLiFy Platform]]

## Provenance
- [[docs-deployment-surfaces]] · [[repo-agentnexlify-claude-md]]
