---
type: project
name: "Chat Widget"
tags:
  - project
  - widget
source_status: source-backed
sensitivity: normal
status: production
last_verified: 2026-06-22
---

# Chat Widget

## Summary
The embeddable JavaScript chat widget — AgentNexLiFy's wedge surface. A tenant adds a
`<script>` tag with `data-api-key="anx_..."` to any site; the widget answers FAQs, captures
leads, and books appointments. In production.

## Critical invariant
- The widget JS must stay **byte-identical** across `widget/agentnexlify-widget.js` and its
  mirror copies (`frontend/public/widget/`, `landing-page-v2/widget/`). Mismatch breaks embeds.
  Enforced by CI + `scripts/sync_widget_assets.py`. See [[Widget Byte-Identical Sync]].

## Tech notes
- Streams replies over SSE (not WebSockets) — see [[SSE not WebSockets]].
- Widget config cached 5 min per Uvicorn worker.

## Related
- [[AgentNexLiFy Platform]] · [[Widget Byte-Identical Sync]] · [[Dashboard]]

## Provenance
- [[repo-agentnexlify-readme]] · [[docs-deployment-surfaces]] · [[dev-knowledge-architecture-decisions]]
