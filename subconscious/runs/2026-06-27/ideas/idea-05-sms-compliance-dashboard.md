# Idea 05 — SMS Compliance Dashboard (Customer Value, Parallel Track)

**Category:** Customer Value  
**Evidence anchor:** Council sprint fix #1 (TCPA SMS opt-out, landed 2026-06-24); customer-gaps.md open item

## What
Add a "SMS Compliance" tab to the tenant dashboard showing:
- Opt-out rate (% contacts who sent STOP)
- Opt-in counts over time
- Blocked contacts list (opted-out)
- Compliance score (0-100: red/yellow/green)
- One-click download of opt-out list for CAN-SPAM audit

Backend: query `leads.sms_opted_out`, `contacts.sms_consent_captured_at`, existing TCPA fields added in council fix #1. Frontend: new `SMSComplianceDashboard.jsx` page, Recharts for trend lines.

## Why
TCPA violations start at $500/violation/text, up to $1,500/day for willful. Small businesses using AgentNexLiFy for SMS automation are exposed. Council fix #1 added backend guards; the dashboard makes compliance legible to non-technical business owners. Reduces churn risk for SMS-heavy tenants (salon, dental, contractor verticals).

## Evidence of demand
- Council fix #1 added TCPA opt-out enforcement backend — no UI yet
- `docs/dev-knowledge/customer-gaps.md` lists SMS compliance visibility as open
- GoHighLevel competitor offers SMS audit trail — our gap
- TCPA class action wave 2024-2025: small businesses primary targets

## Risk
- Parallel track (doesn't depend on widget drift fix)
- Requires migration for any missing columns (none expected — council fix #1 added them)
- Medium effort: 1 backend route + 1 frontend page

## Verdict signal
High customer value, low technical risk, parallel to the widget drift track. Appropriate after Check 13 unblocks.
