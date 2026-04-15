# Customer Support Agent — Sales Spec

## One-line Pitch
"A 24/7 tier-1 support agent that handles 70% of tickets autonomously — and knows when to escalate to a human."

## Problem Solved
SMBs either (a) respond slowly and bleed customers, (b) hire expensive humans for repetitive questions, or (c) both. Meanwhile 70% of tickets are variations of 20 questions.

## Target Customer
- SMB handling 50+ tickets/month
- Has a knowledge base or can build one
- Support across email + chat + SMS (or subset)
- Uses Zendesk, Intercom, Help Scout, Freshdesk, or our widget

## Pricing
| Tier | Setup | Monthly | Scope |
|------|-------|---------|-------|
| Basic | $2,000 | $500 | 1 channel (email OR chat) + up to 100 KB articles |
| Standard | $3,500 | $500 | 2 channels + up to 500 KB articles |
| Premium | $5,000 | $500 | 3+ channels + CRM integration + voice of customer loop |

## Deliverables
- Trained agent with client's KB embedded
- Custom tone + voice matching brand
- Tier classification (L1 auto / L2 human / P0 page)
- Approval gates on refunds, account changes, account deletion
- Integration with existing ticketing tool
- Weekly "top 10 missed questions" report → KB gap-filling
- Monthly CSAT + deflection rate dashboard
- Human handoff with full context

## Integrations Supported
- Email: Gmail, Outlook, Front, Help Scout
- Chat: Intercom, Drift, Crisp, our AgentNexLiFy widget
- SMS: Twilio, Vonage
- Ticketing: Zendesk, Freshdesk, Linear Support
- KB: Notion, Confluence, Help Scout Docs, Intercom Articles, our KB
- CRM: HubSpot, Pipedrive, Salesforce

## Client Requirements
- Sample of 100 recent tickets (training signal)
- KB articles (or we help build from scratch → +$500 setup)
- Brand voice guide
- Escalation rules (who gets paged for what)
- API access to ticketing system

## Setup Timeline
| Day | Milestone |
|-----|-----------|
| 0 | Kickoff + ticket sample + KB handoff |
| 1-4 | KB embedding + classification training |
| 5-7 | Prompt tuning + integration wiring |
| 8-10 | Shadow mode — agent drafts, human sends |
| 11-14 | Supervised mode — auto-send + human QA |
| 15 | Autonomous mode with human escalation gate |

## Success Metrics
- Deflection rate (target 60-75%)
- CSAT on auto-responses (target ≥4.2/5)
- First response time (target <5 min)
- Escalation accuracy (true P0 caught = 100%)
- Cost per ticket (target <$0.50)

## Why Managed Agent
- Multi-hour session = follows complex thread without forgetting
- Approval gates on refunds/cancellations prevent accidents
- Anthropic infra handles scale spikes (Black Friday)
- SOC 2 + data residency inherited
