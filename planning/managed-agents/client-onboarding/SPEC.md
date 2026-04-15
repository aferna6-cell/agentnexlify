# Client Onboarding Agent — Sales Spec

## One-line Pitch
"A 24/7 onboarding coordinator that welcomes every new customer, collects required docs, and triggers your existing workflows — without a human on call."

## Problem Solved
SMB owners lose 30-60 min per new customer on: welcome email, doc collection (IDs, contracts, payment info), CRM setup, first-task kickoff. Scale = missed onboardings + stale CRM + refund requests.

## Target Customer
- SMB with 5+ new customers/month
- Solo ops, bookkeeping, legal intake, contractor intake
- Current process: manual email chains + Google Drive folders

## Pricing
| Tier | Setup | Monthly | Scope |
|------|-------|---------|-------|
| Basic | $1,500 | $500 | 1 entry channel (email OR form) + 2 integrations |
| Standard | $2,250 | $500 | 2 channels + 4 integrations |
| Complex | $3,000 | $500 | 3+ channels + 6+ integrations + custom scoring |

## Deliverables
- Agent instructions tuned to client's industry + brand voice
- Welcome email template (branded)
- Intake form (hosted or embedded)
- Doc collection flow with approval gates
- CRM sync (Supabase, HubSpot, Pipedrive, etc.)
- Slack/email notification on new customer completion
- Onboarding checklist auto-tracking
- Dashboard link showing active onboardings

## Integrations Supported
- Email: Gmail, Outlook, Resend, Postmark
- CRM: HubSpot, Pipedrive, Supabase, Airtable
- Storage: Google Drive, Dropbox, S3
- Chat: Slack, Teams
- Forms: Typeform, Tally, our widget
- Calendar: Google Cal, Calendly

## Client Requirements
- Brand assets (logo, color, voice guidelines)
- Sample of current onboarding emails
- List of required docs + who approves them
- API keys / OAuth for integrations
- 2-hour kickoff call availability

## Setup Timeline
| Day | Milestone |
|-----|-----------|
| 0 | Kickoff call + asset handoff |
| 1-3 | Agent prompt build + integration wiring |
| 4-5 | Internal QA with test customer |
| 6-7 | Client review + tuning |
| 8 | Go-live with first 3 real customers |
| 30 | Post-launch review + prompt tune |

## Success Metrics (reported monthly)
- New customers onboarded (count)
- Avg time to completion (vs baseline)
- Doc completion rate
- Human intervention rate (goal <10%)
- CSAT from customer survey

## Why Claude Managed Agents Over DIY
- No server for client to run
- Approval gates on sensitive actions (send email, charge card) built in
- Anthropic SOC 2 compliance inherited
- Multi-hour session memory means the agent doesn't lose context mid-onboarding
