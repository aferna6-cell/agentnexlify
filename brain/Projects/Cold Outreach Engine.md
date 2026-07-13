---
type: project
name: "Cold Outreach Engine"
tags:
  - project
  - growth
  - outreach
source_status: source-backed
sensitivity: normal
status: live
last_verified: 2026-07-13
---

# Cold Outreach Engine

## Summary
The lead-generation + cold-email pipeline that fills the top of AgentNexLiFy's sales funnel.
It finds real small businesses, verifies their emails, and drips a personalized template to
them via [[Instantly]]. Built and taken live 2026-07-13 (this session). First live campaign:
**"Small Business CT 7/10"** — 371 verified Connecticut small businesses, 0 bounces.

## How it works (pipeline)
1. **Source** — `scripts/leadgen/build_leads.py` pulls businesses from **Google Places**
   (`--source google`, needs `GOOGLE_PLACES_API_KEY`) or free keyless OpenStreetMap
   (`--source osm`). `enrich.py` then scrapes each business site for a **real published email**
   + owner name. OSM has ~zero US SMB coverage → Places is the productive source.
2. **Verify + load** — `scripts/outreach/instantly_lead_engine.py` dedupes candidates against
   the campaign, loads them, verifies **every** email through Instantly's verification API, and
   deletes the invalid ones. Only deliverable addresses stay → protects sender-domain warmup.
3. **Send** — Instantly runs the campaign on its own schedule (Mon–Fri 08:00–22:00 ET, 9 warmed
   inboxes). Per-inbox daily cap is **server-enforced at 20** ("AirMail dynamically manages
   higher limits for best deliverability") — cannot be overridden, by design.

## Key results (2026-07-13)
- 371 verified-deliverable CT leads loaded, **0 bounces** across all loads.
- Real-email enrichment (Places) verified ~50% vs ~20% for guessed `info@` (listicle scraping).
- Template reused from prior campaigns: subject `AI for {{company_name}}`, body → agentnexlify.com.

## Tooling built this session
- `mcp-servers/instantly/` — FastMCP server wrapping Instantly (campaigns, leads, verify).
- `scripts/outreach/instantly_lead_engine.py` (+ tests, `ct_sources.txt`, README) — verify+load engine.
- Reused existing `scripts/leadgen/` (Places/OSM + enrich) — the "engine with the Places key".

## Related
- [[Instantly]] · [[AgentNexLiFy Platform]] · [[MTOptions]] · [[Paid Launch Readiness]]

## Provenance
- This session (2026-07-13); `scripts/outreach/`, `scripts/leadgen/`, `mcp-servers/instantly/`.
