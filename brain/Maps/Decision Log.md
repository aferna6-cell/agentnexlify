---
type: map
name: "Decision Log"
tags:
  - map
  - moc
last_updated: 2026-07-01
---

# Decision Log

Source-backed decisions, newest first.

- 2026-07-01 — Zapier plan_status enforcement (GH #107) approved AUTONOMOUS-EXECUTABLE — cancelled tenants currently retain Zapier API access after subscription ends; security/revenue fix, S effort. Source: commit 8a3b071 (subconscious run 75).
- 2026-07-01 — SMS Compliance Dashboard de-scope rule — run 75 mandate: if the React page isn't shipped, de-scope to backend-only. Backend (`sms_compliance.py` + migration 160) is live; frontend page never started after 10+ days as subconscious winner. Source: commits e225b53, c3298be, 8a3b071.
- 2026-06-28 — Widget-drift topic retired from subconscious permanently (run 70 mandate) — loop stops re-nominating it; `landing-page-v2/` sync stays human-owned because that path is forbidden to the autonomous stack. Drift itself synced 2026-07-01. Source: commit 86890cb + `docs/reminders/widget-drift-URGENT.md`.
- 2026-06-26 — LLM Council SMB onboarding/integration strategy — 9 council fixes shipped same day: TCPA SMS opt-out suppression on every outbound path, per-recipient text-back frequency cap, lead temperature badge, lapsed-integration surfacing, propose-only + recoverable record changes, sell-outcomes copy, no-website onboarding KB fallback, 10DLC/onboarding ops runbooks, label fix. Source: commits 5f3cc47, 9ddfd0e→bcdafc2.
- 2026-06-23 — Kill free trial confirmed SHIPPED (trial banners removed, backend already trial-free, card charged at signup) + all beta tenants converted to paid (owner). Source: [[Open Loops]] round 6.
- 2026-06-23 — Vertical expansion 7→13 verticals (KB packs + SEO pages + onboarding presets per vertical); 13 declared the diminishing-returns stopping point. Source: PRs #366/#367.
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
