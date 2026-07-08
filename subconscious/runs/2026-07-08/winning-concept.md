# Winning Concept — 2026-07-08 (Run 83)

## Recommendation
Add a lead source breakdown chart to the Leads dashboard page — wire `leads.lead_source` to a Recharts `<PieChart>` or `<BarChart>` component showing how leads arrive by channel.

## Why This, Why Now
`docs/dev-knowledge/customer-gaps.md` lists lead source analytics as an open cross-industry gap (all industries, Low effort). The `leads.lead_source` column exists in the DB. Recharts is already installed in `frontend/package.json` (used by AnalyticsPage.jsx). No schema migration needed — this is a read-only query + new UI component. The moratorium is lifted (pending=1 of max=2; adding this winner makes pending=2, at threshold but not over). No higher-urgency items block this run. The KB autopopulate (run 82 winner) was implemented — platform is no longer in operational fire-fighting mode.

The governance note from run 9 says "Lead Source Analytics already implemented in AnalyticsPage.jsx" — but `customer-gaps.md` post-dates that correction and still lists the gap. The specific gap is a per-lead source breakdown on the **Leads page** (where agents review individual leads), not just a general analytics page chart.

## Implementation Sketch

**File: `frontend/src/pages/LeadsPage.jsx`** (or equivalent Leads page)

1. Add a `LeadSourceChart` component:
   ```jsx
   import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';
   ```

2. Query `GET /api/leads/stats?group_by=lead_source&client_id={clientId}` (new endpoint) OR use existing leads data already fetched and group client-side.

3. Component renders a `<PieChart>` with slices for each source (organic, referral, widget, direct, import, unknown). Apply existing color scheme from AnalyticsPage.jsx.

4. Empty state: "No lead source data yet — leads will appear here as they come in."

5. Date range filter: wire to existing filter state if present.

**Backend option** (if client-side grouping insufficient):
- `GET /api/leads/source-stats` returning `{source: string, count: int}[]`
- Scoped by `client_id` from auth context
- Single SQL: `SELECT COALESCE(lead_source, 'unknown'), COUNT(*) FROM leads WHERE client_id = $1 GROUP BY 1`

**Preferred path:** group client-side on already-fetched leads data if leads are paginated with full dataset. Avoids new endpoint. If leads are paginated and server-side, add the lightweight stats endpoint.

## What This Does NOT Change
- No schema migration
- No widget changes
- No auth changes
- No existing tests broken

## Bonus: Autonomous Companion Action
Nightly review should execute as autonomous bonus (XS effort, SKILL.md edit):
- Add `brain/INGESTION-LOG.md` to Phase 2 "Also read:" block in `.claude/skills/subconscious/SKILL.md`
- One line: `- brain/INGESTION-LOG.md (last 10 lines — connector health signal)`
- Zero risk — additive read-only instruction

## Confidence
**HIGH** — column exists, Recharts installed, AnalyticsPage.jsx pattern available to mirror, customer-gaps.md confirms the gap is open, moratorium budget safe.

## Autonomous-Executable?
**NO** — frontend UI change requires human review. But LOW risk and reversible.

## Pending Count After This Run
Run 79 (brain connectors): pending_human → still pending_human
Run 83 (this winner): pending_approval → newly pending
**Total pending: 2 of max 2. At threshold. Safe.**
