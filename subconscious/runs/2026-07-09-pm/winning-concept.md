# Run 85 — Winning Concept: Lead Source Analytics Dashboard

**Date:** 2026-07-09-pm  
**Run:** 85  
**Category:** customer_value  
**Effort:** L  
**Confidence:** HIGH  
**Status:** pending_approval

---

## Problem

7 real leads have been captured since the 2026-06-23 deploy. We have zero visibility into acquisition source. MTOptions alone generated 4 of 7 — but we don't know if that's organic search, referral, direct, or something else. The `source` column exists in the `leads` table and has been unpopulated and unvisualized since the widget launched.

Without source attribution, the user can't answer: "Is our SEO working? Are referral links converting? Which traffic channel should we invest in?"

This gap has been in `docs/dev-knowledge/customer-gaps.md` since run 2 (83 subconscious cycles ago).

---

## Proposed Action

Create one GH issue labeled `ai-ready` for the issue-to-pr-loop to implement:

**Issue title:** `feat(analytics): add lead source breakdown chart to analytics page`

**Issue body (use verbatim):**
```
## What
Add a bar chart showing lead acquisition sources to the Analytics page.

## Why
7 real leads captured since 2026-06-23; source attribution unknown.
The `source` column exists on `leads` table but has no dashboard visualization.

## Implementation

### Backend (`backend/routers/`)
Add endpoint: `GET /api/leads/source-breakdown`

```python
# In backend/routers/leads.py (or analytics.py if it exists)
@router.get("/leads/source-breakdown")
async def lead_source_breakdown(
    current_tenant: dict = Depends(get_current_tenant),
    db: Client = Depends(get_supabase_client),
):
    client_id = current_tenant["client_id"]  # CRITICAL: client_id NOT tenant_id
    result = db.table("leads") \
        .select("source") \
        .eq("client_id", client_id) \
        .execute()
    from collections import Counter
    counts = Counter(row.get("source") or "Direct / Unknown" for row in result.data)
    return [{"source": k, "count": v} for k, v in counts.most_common()]
```

**Invariants:**
- Use `client_id` NOT `tenant_id` — this is a critical schema invariant
- NO `from __future__ import annotations` in this file
- Auth required via existing `get_current_tenant` dependency
- RLS enforced by Supabase; Python query MUST also filter by `client_id`

### Frontend (`frontend/src/pages/AnalyticsPage.jsx`)
Add BarChart using Recharts (already installed):

```jsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
// ... in component after existing charts:
const [sourceData, setSourceData] = useState([]);

useEffect(() => {
  fetch("/api/leads/source-breakdown", { headers: { Authorization: `Bearer ${token}` } })
    .then(r => r.json())
    .then(setSourceData)
    .catch(() => {});  // silent fail — non-critical chart
}, []);

// In JSX:
{sourceData.length > 0 && (
  <div className="chart-card">
    <h3>Lead Sources</h3>
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={sourceData}>
        <XAxis dataKey="source" tick={{ fontSize: 11 }} />
        <YAxis allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="count" fill="#6366f1" />
      </BarChart>
    </ResponsiveContainer>
  </div>
)}
```

## Tests
- Unit: `GET /api/leads/source-breakdown` returns grouped counts for mock lead data
- Unit: query scopes to `client_id` (assert `client_id` in query, not `tenant_id`)
- Unit: null/empty source rows count as "Direct / Unknown"
- Manual: Chart renders in AnalyticsPage with real prod data (0 leads = no chart shown)

## Acceptance Criteria
- [ ] Endpoint returns source breakdown scoped to `client_id`
- [ ] Null/empty source → "Direct / Unknown" bucket
- [ ] Bar chart visible on AnalyticsPage when data exists
- [ ] No chart rendered when zero leads
- [ ] All tests pass; no `from __future__ import annotations` added
```

---

## Why This Wins

1. **Mandate match** — `run_85_mandate`: "revisit lead source analytics dashboard as run 85 winner if pipeline confirmed healthy."
2. **83-run parking lot** — longest-deferred item in customer-gaps.md. Deferral was bandwidth, not priority.
3. **GH #399 structurally fixed** — dfa8201 added PAT fallback; issue-to-pr-loop can now pick up ai-ready issues without dying on PAT expiry.
4. **L effort, zero new deps** — Recharts installed, source column exists, one endpoint + one chart = 1-2h implementation.
5. **Direct customer value** — small businesses want to know "where are my leads coming from?" before investing in any channel.
6. **Safe for autonomous implementation** — no schema migration, no auth change, no widget touch. Pure endpoint + chart.

---

## What This Does NOT Do

- Does not add UTM tracking (separate issue; upstream of this chart)
- Does not backfill source data on old leads (null → "Direct / Unknown" handles this)
- Does not change lead capture flow

---

## Run 86 Mandate

1. Verify GH issue was created for Lead Source Analytics and assigned `ai-ready` label
2. Verify issue-to-pr-loop picked it up (draft PR opened within 24h of issue creation)
3. If no PR after 24h: check loop health via Step 9D in nightly report
4. Verify Step 9E was added to `.claude/skills/nightly-commit-review/SKILL.md` by nightly-2026-07-10
5. Verify `ops/credential-rotation-schedule.md` was created (run 84 pending_autonomous item)
6. If both run 84 items confirmed: revisit warm lead recovery (Sunset Mobile Detailing + Niko's Consulting)
