# Photo-quote default pricing rules

Platform-curated baseline pricing per vertical for the photo-quote feature
(issue #43, `specs/photo-quote_spec.md` rollout step 5). Each tenant starts on
these defaults and overrides them in the dashboard (future issue) or keeps them.

## Files

One JSON per vertical: `plumbing`, `roofing`, `hvac`, `auto_body`,
`landscaping`, `pest`. Each file is stored verbatim as
`tenant_pricing_rules.rules_jsonb` and injected into the Claude vision prompt by
`backend/services/photo_quote_prompts.py::build_vision_prompt` (#38).

### Shape

```json
{
  "_meta": {
    "industry": "plumbing",
    "currency": "USD",
    "source": "HomeAdvisor/Angi 2025 national averages — ...",
    "source_urls": ["https://...", "https://..."],
    "note": "Platform default pricing — tenants should customize ..."
  },
  "damage_types": {
    "<damage-type>": {
      "minor": {"low": <int>, "high": <int>},
      "major": {"low": <int>, "high": <int>}
    }
  }
}
```

Every file carries **≥6 damage types**. Ranges are USD and deliberately broad —
they are starting points, not quotes.

## Sources

Ranges are sourced from **HomeAdvisor / Angi 2025 national-average cost
guides**; the exact URLs are recorded in each file's `_meta.source_urls`.
Plumbing is validated by the pilot; the other five are refined post-pilot.

## Regenerate

The files are curated data, not generated output — edit the JSON directly, keep
it valid, and preserve the `_meta` + `damage_types` shape. Validate:

```bash
python3 -c "import json,glob;[ (lambda d: (_ for _ in ()).throw(SystemExit('bad'+p)) if len(d['damage_types'])<6 else print(p,'OK'))(json.load(open(p))) for p in glob.glob('backend/data/photo_quote_defaults/*.json')]"
```

## Seeding

```bash
# preview (no writes)
python3 backend/scripts/seed_photo_quote_pricing.py --dry-run

# apply — upserts one row per (eligible tenant, vertical); idempotent
python3 backend/scripts/seed_photo_quote_pricing.py
```

The seed upserts on the `tenant_pricing_rules (client_id, industry)` unique
constraint (migration 108), so re-running refreshes the defaults without
duplicates and without touching a tenant's own `min_confidence_threshold`.

### Prerequisite (owner action)

The spec targets **Pro-tier tenants with `photo_quote_enabled = true`**. That
flag column is **not yet in the schema** — a prerequisite migration must add
`photo_quote_enabled boolean not null default false` to `tenants`. Until then
the seed selects paid-plan tenants by default; pass `--require-flag` once the
column exists to honor the spec's eligibility exactly.
