# Idea 5: Lead Source Analytics — Wire Existing Column to Dashboard

**Evidence:** `docs/dev-knowledge/customer-gaps.md` lists: "Lead source analytics — All simulations — source column exists, no dashboard visualization — Low effort." Column `leads.lead_source` exists (confirmed by multiple prior runs). Customer-gaps.md explicitly rates this as LOW effort with HIGH cross-industry impact (affects every vertical: plumber, dental, salon, real estate, lawyer). No recent commits touch this gap. Issue tracker has no open issue for this feature. This is a revenue-differentiation gap — Birdeye/Podium at $300-600/mo show lead source breakdowns; we have the data but not the chart.

**Action:** Create GH issue for "Add lead source breakdown to dashboard Leads page" — pie/bar chart of `leads.lead_source` values using Recharts (already installed). Fetch data from existing `/api/v1/leads` endpoint. No new backend endpoint or migration needed. Mark as `ai-ready` for issue-to-pr-loop after pending_approvals clears.

**Impact:** Closes a low-effort, high-visibility customer gap. Adds tangible value to chatbot + agent_os plan subscribers. Competes better with Birdeye/Podium on analytics. ~4h frontend work.

**Category:** customer_value

**Confidence pre-debate:** MEDIUM — good idea but timing is wrong: pending_approvals already at 1 (heading to 2 with #107 if chosen). Adding a third would trigger moratorium. Better as parking lot for run 83.
