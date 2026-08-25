# Outreach lead engine

Automates topping up an Instantly cold-email campaign with **verified,
deliverable** CT small-business leads. Built for the `Small Business CT`
campaign but campaign-agnostic.

## What it does

`instantly_lead_engine.py` runs a deterministic pipeline:

1. Read candidate businesses (company + website domain) from a CSV.
2. Build `info@<domain>` when no explicit email is given.
3. Dedupe against leads already in the target campaign.
4. Load the new ones into the campaign.
5. Verify every new email via Instantly's verification API.
6. Delete the invalid ones so bounces never hit the sending domains.

The campaign sends on its own schedule. The engine only adds good leads.

## Why verification matters

Role addresses (`info@…`) guessed at real domains bounce ~60% of the time.
A bounce rate over ~3-5% gets sending inboxes suspended. Verification is the
guardrail: only addresses Instantly confirms as deliverable stay in the
campaign. In practice ~33% of researched businesses survive to a real send.

## Run it manually

```bash
export INSTANTLY_API_KEY=...            # base64 Instantly v2 key (never commit)
export INSTANTLY_CAMPAIGN_ID=6b3239fe-9368-407b-9ab8-bb5c7642e3f8
python scripts/outreach/instantly_lead_engine.py \
    --candidates candidates.csv \
    --target 350                        # stop once campaign hits 350 leads
```

`candidates.csv` needs a header row with `company_name` plus one of
`domain` / `website` / `email`.

## Sourcing candidates

Two sources, either produces the same `candidates.csv`:

1. **Keyless (default, 2026-08-25): `osm_lead_source.py`** — pulls businesses
   from OpenStreetMap via the public Overpass API. No API key at all, which
   removes the `GOOGLE_PLACES_API_KEY` blocker that stalled the loop
   (Open Loops 2026-07-13). Only businesses publishing a real `website` tag
   are emitted (aggregator/social hosts filtered), so every row is
   role-email-able. Presets cover all 13 launched verticals.

   ```bash
   python3 scripts/outreach/osm_lead_source.py \
       --vertical salon --area "Connecticut" \
       --out scripts/outreach/candidates/salon-ct.csv --limit 300
   python3 scripts/outreach/osm_lead_source.py \
       --vertical plumber_hvac --area "Connecticut" \
       --out scripts/outreach/candidates/plumber-ct.csv --limit 300
   ```

   Three Overpass mirrors are tried in order. Sandboxed CI environments may
   block or catch mirrors mid-outage — run from any normal machine or a
   Routine with standard egress. Data (c) OpenStreetMap contributors (ODbL).

2. **Directory pages: `ct_sources.txt`** — high-yield directory pages
   (inven.ai, expertise.com) that show many businesses with real domains per
   page. The scheduled driver fetches those, extracts `company | domain`
   pairs, and writes `candidates.csv`. Rotate cities/verticals to keep
   finding fresh businesses.

## Automated schedule

A weekly **Routine** (Claude Code scheduled trigger) drives the full loop:
fetch sources -> extract candidates -> run engine -> report counts. It tops
the campaign up toward the target and stops when reached.

**Required for autonomous runs:** `INSTANTLY_API_KEY` must be set in the
Claude Code **environment variables** (not just a shell), so a fresh
scheduled session can authenticate. Add it in the environment settings for
this repo. Without it the engine exits with a clear error and sends nothing.

## Tests

```bash
python -m pytest scripts/outreach/test_instantly_lead_engine.py \
                 scripts/outreach/test_osm_lead_source.py
```

Covers the pure helpers (domain normalization, email building, dedupe,
Overpass query building, tag extraction). Network paths are not exercised
in tests.
