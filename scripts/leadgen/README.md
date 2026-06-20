# AgentNexLiFy Lead-Gen CLI

Internal outreach tool. Pulls local businesses from Google Places **or**
OpenStreetMap (keyless), enriches each with a scraped email address,
deduplicates, and writes a CSV ready to import into Instantly, Apollo, or
similar cold-email platforms.

## Quick Start

```bash
# Keyless — uses OpenStreetMap, no API key needed:
python -m scripts.leadgen.build_leads --vertical "roofing" --city "Austin, TX" --out leads.csv

# Google Places (richer coverage) — set a key first:
export GOOGLE_PLACES_API_KEY="your_api_key_here"
python -m scripts.leadgen.build_leads --vertical "roofing" --city "Austin, TX" --out leads.csv --max 200
```

Output columns: `name, category, phone, website, email, owner_name, contact_form, address, city, rating, place_id, demo_url`

`owner_name` (best-effort, from the site's about/contact pages — blank unless confident) and `contact_form` (a contact/quote-page URL when no email is found) let you personalize with `{{owner_name}}` and reach the ~60% of businesses that have no scrapeable email via their form.

## Sources

`--source auto` (default) uses **Google Places** when `GOOGLE_PLACES_API_KEY`
is set, otherwise the free **OpenStreetMap** (Overpass) source. Force one with
`--source google` or `--source osm`.

| Source | Key | Cost | Coverage |
|--------|-----|------|----------|
| `google` | required | ~$32/1k searches | broadest SMB coverage |
| `osm` | none | free (ODbL) | strong for trades (`craft=roofer/plumber/electrician`) + retail; patchier for some service verticals |

OSM resolves the city to an area via Nominatim, then queries Overpass for the
vertical's tags. Unknown verticals fall back to a `craft`/`shop`/`office` guess.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_PLACES_API_KEY` | Google Places API key. Required only for `--source google` (or `auto` when you want Google). OSM needs nothing. |

Optional:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEMO_URL_TEMPLATE` | URL template for the demo column. Placeholders `{business}`, `{vertical}`, `{place_id}` are URL-encoded before substitution. | `https://agentnexlify.com/demo?business={business}&type={vertical}&ref={place_id}` |

## Arguments

```
--vertical TEXT   Business type (e.g. "roofing", "dental", "HVAC"). Required.
--city TEXT       City to search (e.g. "Austin, TX"). Required.
--out TEXT        Output CSV file path. Default: leads.csv
--max INT         Max leads to pull. Default: 200
--api-key TEXT    API key override (falls back to GOOGLE_PLACES_API_KEY).
--source TEXT     auto (default) | google | osm. See Sources above.
```

## Google Places API Notes

### Which API is used

The script uses the Google Places API (New, v1) text search endpoint:

    POST https://places.googleapis.com/v1/places:searchText

Authentication is via the `X-Goog-Api-Key` request header. This is the
current Maps Platform API, not the legacy Places API.

### Cost

Rough estimates from Google Maps Platform pricing (2024):

- Text Search (New): approximately $32 per 1,000 requests
- The script fetches up to 3 pages of 20 results per run = 3 API calls max
- Cost per run: roughly $0.10 or less for a single city + vertical query

There is no Details API call in this script. All data comes from the
Text Search response fields requested via `X-Goog-FieldMask`.

### 60-result cap + grid-by-neighborhood tip

The Google Places Text Search API returns at most 60 results per query
(3 pages x 20 results). For large metros, results may not cover the full
city. To get broader coverage, run the script once per neighborhood:

```bash
for HOOD in "Austin Heights" "South Congress" "East Austin" "Mueller"; do
  python -m scripts.leadgen.build_leads \
    --vertical "roofing" \
    --city "${HOOD}, Austin, TX" \
    --out "leads_${HOOD// /_}.csv"
done
```

Combine the per-neighborhood CSVs and deduplicate with `merge_leads.py`:

```bash
python -m scripts.leadgen.merge_leads --glob "leads_*.csv" --out leads.csv
```

## Merging + Instantly import (merge_leads.py)

`merge_leads.py` combines multiple `build_leads.py` outputs into one
import-ready file. It deduplicates by `place_id` (so a business found in two
overlapping searches is emailed once), prefers the enriched copy when a
duplicate has an email the other lacked, and drops rows with no email by
default.

```bash
# merge everything matching a glob
python -m scripts.leadgen.merge_leads --glob "leads_*.csv" --out leads.csv

# merge explicit files, keep rows that have no email
python -m scripts.leadgen.merge_leads a.csv b.csv --out leads.csv --keep-no-email

# emit Instantly-ready columns (email, company_name, + custom vars)
python -m scripts.leadgen.merge_leads --glob "leads_*.csv" \
  --out instantly.csv --instantly
```

The `--instantly` format maps `name -> company_name` and keeps
`email, owner_name, website, phone, city, category, demo_url, contact_form`. Instantly auto-maps
email/company_name/website/phone; the rest become custom variables usable in a
sequence as `{{demo_url}}`, `{{city}}`, etc.

## Google Maps Platform Terms of Service Caveat

This tool is for internal outreach use only. Read the full Maps Platform
Terms of Service before use. Key restrictions:

1. Do NOT build or sell a permanent database of Places content. Google
   prohibits storing Places data to create a competing product or
   reselling the data to third parties.

2. Refresh data within approximately 30 days. Cached place data
   (name, address, phone, website) should be considered stale after
   roughly 30 days and should be re-fetched if used in a live product.

3. `place_id` is the only field safe to store long-term. Google's ToS
   explicitly allows caching place IDs indefinitely for the purpose of
   refreshing data. All other fields (name, address, phone, website,
   rating) are subject to the 30-day freshness requirement.

4. Display attribution when showing Maps data in any user-facing context.
   The "Powered by Google" logo and attribution text are required on any
   screen that displays Places data.

This script is for building an internal outreach list -- not for
exposing Places data in a product UI. That use case requires additional
attribution and may have different data retention rules.

Reference: https://developers.google.com/maps/terms

## Email Enrichment Notes

The enricher fetches the homepage and `/contact` page of each business
website, extracts email addresses via regex, and filters junk patterns
(image asset extensions, Sentry error emails, Wix template placeholders, etc.).

Email preference order:
1. info@ / contact@ / hello@ / office@ (business-owned)
2. First email found
3. Empty string if no valid email found

Network errors during enrichment are swallowed silently; that business
gets an empty email field.

## Output Format

The CSV is ready to import directly into Instantly or Apollo. Required
fields for most cold-email tools: `name`, `email`, `website`.

The `demo_url` column is pre-populated with a personalized demo link
using the `place_id` as a tracking ref. Customize via `DEMO_URL_TEMPLATE`.
