---
type: decision
decision_date: 2026-03-25
status: active
tags:
  - decision
  - architecture
source_status: source-backed
confidence: high
---

# Decision: SSE, not WebSockets, for Widget Streaming

## Decision
Stream [[Chat Widget]] replies over Server-Sent Events rather than WebSockets.

## Rationale
Simpler and more proxy/CDN-friendly for an embeddable cross-origin widget.

## Consequences
- One-way streaming model; reconnect logic handled on the widget side.

## Related
- [[Chat Widget]] · [[Vendor Stack]]

## Provenance
- [[dev-knowledge-architecture-decisions]]
