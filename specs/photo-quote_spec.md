# Photo-Quote Widget — PRD

**Status:** grilled 2026-04-20, ready for issue staging
**Owner:** Aidan
**Created:** 2026-04-20
**Target tier:** Professional (500 quotes/mo included, $0.15/quote overage via Stripe metered)

## Goal

Tenant widget accepts customer photo → Claude Opus 4.7 vision reads damage/scope → returns quote range using tenant pricing rules. Reduces "schedule inspection" friction for photo-friendly trades.

## Non-goals

- Final binding quotes (always a range + disclaimer)
- Insurance claim estimation
- 3D modeling or AR overlays
- Multi-image analysis v1 (single image only)
- Salon/dental/legal verticals (text flow fine)

## Target users

Tenants in photo-friendly trades: plumbing, roofing, HVAC, auto body, landscaping, pest.

## User stories

1. Customer hits widget → "Get instant estimate" CTA → uploads pipe-leak photo → widget returns `$150-400` + "book inspection to lock in price" CTA.
2. Roofer-tenant customer uploads shingle damage → widget returns range + 3-fork prompt [Try another photo] [Book inspection] [Get text quote] if Claude confidence < vertical threshold (roofing 0.8).
3. Tenant admin sees new `quote_requests` tab in dashboard showing photos + quotes + conversion outcome + monthly usage meter vs 500 cap.

## Acceptance criteria

### Frontend (widget)
- Upload button visible when `tenant.photo_quote_enabled = true`
- Accepts `image/jpeg`, `image/png`, max 10MB, single file
- Shows upload progress + abort
- Renders quote range + confidence + CTA
- Mandatory disclaimer: platform default "Estimate only — final quote subject to inspection" OR tenant-supplied via `tenant_pricing_rules.disclaimer_text`

### Backend
- `POST /api/widget/photo-quote` — accepts multipart {image, client_id, conversation_id}
- Streams image to Claude Opus 4.7 with 3x vision (rules/vision-3x.md)
- Applies `tenant_pricing_rules` via prompt injection
- Returns `{quote_low, quote_high, severity, confidence, summary, needs_human: bool}`
- Persists request+response to `quote_requests` table + links to conversations
- Generates + stores thumbnail (256px long edge) alongside full image
- Increments tenant monthly usage counter; checks 500/mo included cap
- Reports overage usage events to Stripe metered price
- Rate limit: 5 uploads/min per conversation (abuse prevent)
- Hard daily per-tenant quota (default 50/day) to cap vision cost spikes

### Schema
New table `tenant_pricing_rules`:
- `client_id uuid` (FK tenants)
- `industry text` — enum: plumbing, roofing, hvac, auto_body, landscaping, pest
- `rules_jsonb` — tiered severity shape:
  ```json
  {
    "leak": {"minor": {"low": 100, "high": 200}, "major": {"low": 400, "high": 800}},
    "burst": {"minor": {...}, "major": {...}}
  }
  ```
- `disclaimer_text text` — nullable, falls back to platform default
- `min_confidence_threshold numeric` — nullable, falls back to per-vertical constant (plumbing 0.7, roofing 0.8, hvac 0.75, auto_body 0.75, landscaping 0.7, pest 0.7)

New table `quote_requests`:
- `id uuid pk`
- `client_id uuid` (FK)
- `conversation_id uuid` (FK)
- `image_url text` (Supabase Storage, full image)
- `thumbnail_url text` (Supabase Storage, 256px long edge, permanent)
- `full_image_purged_at timestamptz` — set when 30d retention job purges full image
- `quote_low int cents`
- `quote_high int cents`
- `severity text` — minor | major | needs_human
- `confidence numeric`
- `claude_summary text`
- `needs_human bool`
- `created_at timestamptz`

New table `tenant_quote_usage`:
- `client_id uuid` (FK, pk)
- `period_start date` (pk)
- `quote_count int default 0`
- `overage_count int default 0`
- Used to drive Stripe metered reporting + in-dashboard meter

Retention job (cron daily):
- Delete `quote_requests.image_url` where `created_at < now() - 30d` AND `full_image_purged_at IS NULL`
- Set `full_image_purged_at = now()`
- Thumbnail + metadata retained indefinitely

### Widget byte-identical
Any widget JS change MUST sync `widget/agentnexlify-widget.js` + `frontend/public/widget/agentnexlify-widget.js`. See CLAUDE.md Rule 4.

## Success metrics

- 30% photo→quote→appointment conversion (baseline text-only: ~15%)
- p95 latency <6s including vision
- <5% tenant-reported quote errors month 1
- Upsell: 10% Growth-tier tenants upgrade to Professional to unlock

## Risks

| Risk | Mitigation |
|---|---|
| Tenant liability on wrong quote | Disclaimer required in widget + T&Cs |
| Vision token cost 5x text | Tier-gate + per-tenant monthly quota |
| Widget mismatch (byte-identical rule) | Pre-commit check on both paths |
| Customer photo PII (license plates, faces) | Blur pass before Claude call + retention policy |
| Industry-specific accuracy | 2-week plumbing-first pilot gates wider rollout; per-vertical confidence defaults (roofing 0.8 strictest) |

## Dependencies

- Supabase Storage bucket `photo-quotes` with RLS per tenant
- Claude Opus 4.7 access (already wired `backend/services/llm_runtime.py`)
- Vision 3x rules (already in `.claude/rules/vision-3x.md`)
- New migration NNN for 3 tables (`tenant_pricing_rules`, `quote_requests`, `tenant_quote_usage`)
- Stripe metered price SKU for $0.15/quote overage billing

## Resolved decisions (grill-me 2026-04-20)

1. **Verticals v1:** all 6 at launch — plumbing, roofing, HVAC, auto body, landscaping, pest (option A)
2. **Pricing format:** tiered by severity — `{damage_type: {minor: {low, high}, major: {low, high}}}` (option B)
3. **Retention:** thumbnail + metadata permanent, full image purged at 30d (option D)
4. **Multi-image:** v2 follow-up ~6 weeks post-GA — additive schema change `image_url` → `image_urls text[]`
5. **Liability:** platform default disclaimer ships as-written + tenant override via `disclaimer_text` column; lawyer tightens after 2-week plumbing pilot (option C+D)
6. **Revenue:** Pro tier + 500 quotes/mo included + $0.15/quote overage via Stripe metered (option C)
7. **Confidence threshold:** per-vertical defaults (plumbing 0.7, roofing 0.8, HVAC 0.75, auto body 0.75, landscaping 0.7, pest 0.7), tenant override via `min_confidence_threshold` (option D)
8. **Human-handoff flow:** 3-fork explicit customer prompt — [Try another photo] [Book inspection] [Get text quote] (option C)

## Rollout

1. Migration — 3 new tables (`tenant_pricing_rules`, `quote_requests`, `tenant_quote_usage`) + retention cron
2. Backend route `/api/widget/photo-quote` + unit tests + per-vertical confidence constants + Stripe metered wiring
3. Widget UI — upload button, thumbnail preview, quote render, 3-fork low-confidence handoff, byte-identical sync
4. Admin dashboard — `Quote Requests` tab + usage meter against 500/mo cap
5. Seed default `tenant_pricing_rules` for all 6 verticals (platform-curated baseline rules)
6. Pilot: 3 plumbing tenants, 2 weeks, gather error rates + legal tightens disclaimer
7. Expand pilot: roofing, HVAC, auto body, landscaping, pest (1-2 tenants each)
8. GA on Professional tier after pilot clears <5% error threshold
9. v2 (~6 weeks post-GA): multi-image — schema `image_url` → `image_urls text[]`, widget multi-upload UI

## Skipped scope

- Video uploads (way too expensive)
- AR/3D preview (out of scope for v1)
- Integrations with estimating software (JobTread, QuickBooks) — separate spec
