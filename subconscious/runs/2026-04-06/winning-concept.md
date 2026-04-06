# Winning Concept — 2026-04-06

## Recommendation
Add a "Lead Sources" chart panel to the Analytics or Leads dashboard page that visualizes the existing `leads.source` column data using Recharts (already a dependency), backed by a single GROUP BY query on the `leads` table.

## Why This, Why Now
The `customer-gaps.md` document — populated from 7 industry simulation cycles — explicitly lists "Lead source analytics" as an open cross-industry gap rated Low Effort: "Source column exists, no dashboard visualization." The `source` column was deliberately added in migration 022 (cycle 122, commit for lead source tracking across all 6 industry types) but has never been surfaced to business owners. In the same period, the repo delivered 3 straight days of high-complexity work (centralized LLM runtime, onboarding flow, E2E smoke tests, 59 new tests) — a low-effort, high-visibility customer value win is the right counterweight. Closing this gap gives every tenant on every plan direct ROI evidence of the widget ("30% of leads came from your chat widget"), which directly reduces churn and strengthens competitive positioning against GoHighLevel and Podium, both of which surface lead source data.

## Implementation Sketch
1. **Backend:** Add `GET /api/leads/source-stats` endpoint in `backend/routers/leads.py`. Query: `SELECT source, COUNT(*) as count FROM leads WHERE client_id = :tenant_id GROUP BY source ORDER BY count DESC`. Return `[{"source": "widget", "count": 42}, ...]`. NULL source values should be mapped to `"direct"` or `"unknown"` in the query (use `COALESCE(source, 'unknown')`).
2. **Frontend:** Locate the Analytics page (`frontend/src/pages/Analytics.jsx` or equivalent). Add a `<LeadSourceChart>` component using `PieChart` or `BarChart` from Recharts. Fetch from `/api/leads/source-stats` on mount.
3. **Empty state:** If all sources are NULL/unknown, show a helpful CTA: "Lead sources will appear here once your widget captures leads. Make sure your widget is live!"
4. **Auth:** The endpoint must be JWT-guarded (same pattern as other leads endpoints) — use `client_id` from JWT claims, NOT `tenant_id`.
5. **Test:** Add 2-3 test cases to `tests/test_untested_routers_crud.py` or a new `tests/test_lead_source_stats.py`: (a) tenant with mixed sources returns grouped counts, (b) tenant with all NULL source returns `unknown` bucket, (c) unauthenticated request returns 401.
6. **Commit:** `feat: add lead source analytics chart to dashboard — closes cross-industry gap`

## What This Replaces
Previous active direction: "Update 4 stale skills per weekly discovery" (run 2026-04-04, status: pending_approval, already committed as ec4e544). That was a workflow improvement; this run pivots to customer value per the diversification rule.

## Confidence
HIGH — Evidence is triple-verified: (1) column confirmed in schema, (2) explicitly listed in customer-gaps.md with "Low Effort" rating, (3) Recharts is already installed and used on the dashboard. Implementation risk is minimal — read-only query, additive frontend component, no schema changes needed.
