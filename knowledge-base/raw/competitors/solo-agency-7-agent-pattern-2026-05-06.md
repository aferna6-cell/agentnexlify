# Solo Web-Agency 7-Agent Pattern — Competitive Intel

Captured 2026-05-06. Source: viral thread + tactical breakdown about a solo operator running a 7-agent Claude Code Router system selling landing pages to local SMBs.

## Claimed numbers (UNVERIFIED — treat as illustrative)
- 47 SMB clients/month at $400 each → ~$18,800 MRR claimed
- $480/month API spend (3M tokens/day on Sonnet 4.6)
- 218 businesses scanned/day on Google Maps
- 30 cold messages/day, 14% reply rate, 5 positive replies, 3 Zoom bookings/Saturday
- 30-50% close rate from positive reply

## The 7-agent system

Single orchestrator on Claude Code Router, file-system shared state at `/Users/dev/maps-agency`, no in-memory shared state, MCP-based tool access.

| Agent | Role |
|-------|------|
| Scout | Walks Google Maps in selected cities. Finds: 5+ years on map, <50 reviews, no website OR site from 2014, high ratings |
| Diagnoser | Per lead: 50-word diagnosis, hero angle, industry-matched tone, <70-word cold message |
| Builder | Generates Lovable landing-page mockup for top 5 leads/day (sharpest diagnoses + biggest gap) |
| Filmer | 5 screenshots of mockup → Higgsfield 10-sec vertical 1080x1920 video, soft zoom |
| Pitcher | Sends cold message via channel matched to niche (email/SMS/IG DM/LinkedIn) |
| Checker | Runs every message through evals: personalization, AI markers, buzzword absence — before send |
| Mobile | Lives in iPhone app, handles positive replies in real time, books Zoom in Calendly while owner is out |

## Bounded autonomy rule (the part worth stealing)

Orchestrator escalates to human approval ONLY when:
- Deal value exceeds $3,000
- Daily reply rate in a niche drops below 12%

Everything else runs autonomous. KPI-drift escalation, not confidence-drift escalation.

## Stack
- Claude Sonnet 4.6 across all 7 agents
- MCP servers for tool access (Lovable, Higgsfield, Calendly, Google Maps, send channels)
- File system as shared state (no race conditions, no shared memory)
- Local sandbox at `/Users/dev/maps-agency`
- Same API key forwarded to Claude Code on iPhone for the Mobile agent

## What's real vs hype

**Real (proven patterns):**
- Pre-built mockup + video as cold-outreach opener — known to lift reply rates
- File-system shared state for multi-agent coordination — matches AgentNexLiFy compound-engineering pattern
- Niche-narrow lead gen ("cosmetic dentists in West Austin") — standard playbook
- KPI-bounded autonomy — concrete pattern, not generic "human in the loop"

**Hype / suspicious:**
- $18,800 revenue figure — anecdotal, viral-thread shape, no source
- 14% cold reply rate across 4 channels — top-decile, not typical (industry avg 3-8%)
- "Claude Code on iPhone agent" — that's the mobile app, not a separate runtime
- 3M tokens/day on Sonnet ≈ $9/day input alone; math checks if cache hits ~95%

## Patterns adopted into AgentNexLiFy

1. **KPI escalation thresholds** in managed_agents_registry — see `backend/services/agent_escalation.py` (added 2026-05-06). Agents wake human on KPI drift (booking rate, qualified-lead rate, deal size), not just confidence drop.

2. **Live mockup widget for cold outreach** — PRD draft at `specs/live-mockup-widget_spec.md` (2026-05-06). Different angle (chat widget, not landing page) but same psychological hook.

## Patterns explicitly REJECTED

- Pivot to selling landing pages — crowded space (GoHighLevel + every YC AI receptionist)
- Lovable/Higgsfield stack — different product surface
- "Mobile agent" framing — Claude Code mobile app already covers this

## Cross-refs
- `.claude/skills/compound-engineering/SKILL.md` — already implements multi-agent file-system state pattern
- `backend/services/managed_agents_registry.py` — agent handles
- `backend/services/agent_escalation.py` — KPI threshold module (new)
- `specs/live-mockup-widget_spec.md` — mockup widget PRD (new)
- `knowledge-base/raw/competitors/competitor-landscape-2026-04-18.md` — broader competitor map

## Re-evaluate when
- Numbers get independently sourced (treat as fiction until then)
- Anyone in our network reports replicating the reply rate
- Mockup-widget feature ships and we have real conversion data to compare
