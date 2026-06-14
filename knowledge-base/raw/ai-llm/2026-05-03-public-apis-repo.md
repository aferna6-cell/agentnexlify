# Public APIs Repo — Free Endpoint Reference

Source: https://github.com/public-apis/public-apis (323K stars, MIT). Triaged 2026-05-03 from Hassid-style listicle.

## Verdict
Marginal value for AgentNexLiFy. Bookmark for future widget context features. No implementation now.

## Why marginal
- Lead enrichment already covered (Clay, ZoomInfo via brand-voice plugin)
- KB autopopulate already runs twice daily
- Most listed APIs irrelevant to small-business SaaS use case
- Free-tier rate limits unsuitable for multi-tenant fan-out without caching layer

## Candidate APIs for tenant verticals (defer until vertical pulls demand)

| API | Use case | Auth | HTTPS |
|---|---|---|---|
| Open-Meteo (open-meteo.com) | Weather context for landscapers, painters, roofers, power-washers | None | Yes |
| Nominatim (nominatim.org) | Geocoding for service-area routing, address validation in widget | None (1 req/s ToS) | Yes |
| Nager.Date (date.nager.at) | Holiday calendar for appointment-booker auto-skip | None | Yes |
| Open Holidays API (openholidaysapi.org) | Regional holidays beyond Nager scope | None | Yes |
| FreeIPAPI (freeipapi.com) | Tenant analytics geo-enrichment | None | Yes |

## When to implement
Trigger conditions:
1. Vertical-specific tenant onboarding asks for weather-aware messaging
2. Widget needs address autocomplete + service-area gating
3. Appointment booker needs holiday-skip logic past current `national_holidays` table
4. Tenant analytics dashboard needs geo breakdown without paid IP service

## Anti-patterns
- Never call free APIs directly from widget JS (CORS + rate limit + tenant abuse vector)
- Never skip caching layer — Supabase table or Redis for hot keys
- Never trust free-tier SLA — wrap in circuit breaker, fall back to null
- Never ship without ToS review per API (Nominatim has hard 1 req/s rule)

## Cross-refs
- `backend/services/automation/` — where appointment-booker skip-logic would live
- `widget/agentnexlify-widget.js` — never call third-party APIs from here
- `migrations/` — `national_holidays` table already exists; check before adding holiday API
- Upstream: github.com/public-apis/public-apis
