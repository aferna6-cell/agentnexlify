# Idea 1 — Lead Source Analytics Dashboard

**Category:** customer_value
**Effort:** S (Low — column exists, Recharts installed)
**Confidence:** HIGH

## What
Wire `leads.lead_source` column to a Recharts pie/bar chart on the frontend Leads dashboard page (`frontend/src/pages/Leads.jsx` or `LeadsPage.jsx`). Allow filtering by date range.

## Evidence
- `docs/dev-knowledge/customer-gaps.md` lists "Lead source analytics" as open cross-industry gap (confirmed LOW effort, all industries).
- `leads.lead_source` column exists in DB (confirmed via schema-log.md and customer-gaps.md).
- Recharts already installed in `frontend/package.json` (used in existing analytics pages).
- KB autopopulate (run 82 winner) now in GH Actions — moratorium lifted to pending=1 of max=2. Budget permits one customer-value item now.
- `frontend/src/pages/` already has `AnalyticsPage.jsx` with Recharts examples to mirror.
- Run 9 governance note: "Lead Source Analytics (run 2) already implemented in AnalyticsPage.jsx" — but customer-gaps.md still lists it as OPEN gap. Gap is on the Leads page specifically, not just Analytics. Two separate surfaces.

## What Does "Implemented" Mean
Run 2 built a generic analytics chart. customer-gaps.md (written later, cross-industry review) lists lead source analytics as still open because:
1. Chart may be on Analytics page, not Leads page where agents look
2. Per-tenant filtering and source breakdown are likely absent
3. Customer-gaps.md post-dates run 2 correction and still flags it

Scope: add a `LeadSourceChart` component to the Leads page showing breakdown by source (organic, referral, widget, direct, etc.) with date range filter.

## Impact
- All tenants immediately see where leads originate without navigating to Analytics
- Closes a cross-industry gap flagged in customer-gaps.md
- Low implementation risk: read-only query, display-only UI, no new migrations

## Autonomous-Executable?
NO — frontend UI change requires human review of layout. But LOW risk, no schema changes, no auth changes.

## Implementation Sketch
1. `frontend/src/pages/LeadsPage.jsx` (or `Leads.jsx`) — add `LeadSourceChart` component
2. Query: `SELECT lead_source, COUNT(*) FROM leads WHERE client_id = ? GROUP BY lead_source`
3. Recharts `<PieChart>` or `<BarChart>` — mirror AnalyticsPage.jsx pattern
4. Date range filter via existing filter state
5. Empty state: "No lead source data yet" if all sources are null
