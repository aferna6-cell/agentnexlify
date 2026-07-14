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

`ct_sources.txt` lists high-yield directory pages (inven.ai, expertise.com)
that show many businesses with real domains per page. The scheduled driver
(below) fetches those, extracts `company | domain` pairs, writes a
`candidates.csv`, then runs the engine. Rotate cities/verticals in
`ct_sources.txt` to keep finding fresh businesses.

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
python -m pytest scripts/outreach/test_instantly_lead_engine.py
```

Covers the pure helpers (domain normalization, email building, dedupe).
Network paths are not exercised in tests.
