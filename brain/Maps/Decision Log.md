---
type: map
name: "Decision Log"
tags:
  - map
  - moc
last_updated: 2026-06-22
---

# Decision Log

Source-backed decisions, newest first.

- 2026-06-15 — [[2026-06-15 Plan Repricing]] — collapse to `chatbot`/`agent_os` (drift open).
- 2026-06-09 — [[2026-06-09 Agent OS Production Merge]] — Agent OS becomes the only prod agent path.
- 2026-05-25 — [[Agent OS Graph Memory]] — defer, then build during the prod merge.
- 2026-06 — [[Kill Trial Charge On Signup]] — remove 7-day trial; charge at signup (reversed #299).
- 2026-06 — [[Remove Free Tier Gate Signup]] — no free signup; gate behind payment.
- 2026-06 — [[Agent OS As Product Spine]] — agent-first UI; retire 18 standalone pages.
- 2026-06 — [[Retire Marketing Addon Into Agent OS]] — drop the standalone add-on SKU.
- 2026-04-18 — [[Sell Vertical Packs]] — vertical-first GTM, not generic chatbot.
- (dated in ADR) — [[SSE not WebSockets]] — widget streaming choice.
- (standing) — [[FastAPI without ORM]] — raw SQL numbered migrations.
- (standing) — [[JWT for Auth Only]] — display data from live API.

## Standing invariants (decision-like)
- [[client_id vs tenant_id]] · [[Widget Byte-Identical Sync]] · no `__future__` annotations.

## Related
- [[Home]] · [[Product Map]]
