# Project Management Agent — Sales Spec

## One-line Pitch
"A PM who never forgets. Triages every task, chases owners, flags slippage, writes status updates — so your humans can build, not manage."

## Problem Solved
PM work is 40% administrative (status updates, chase emails, standup prep, sprint retro docs) and 60% judgment (what to prioritize, who's blocked). SMBs can't afford a full PM but suffer without one.

## Target Customer
- SMB with 5-30 people
- Uses Linear, Jira, Asana, ClickUp, Notion, or GitHub Issues
- Currently: founder or senior eng does PM work on the side
- Pain: missed deadlines, unclear ownership, stale boards

## Pricing
| Tier | Setup | Monthly | Scope |
|------|-------|---------|-------|
| Basic | $2,500 | $500 | 1 PM tool + standup automation + deadline tracking |
| Standard | $3,750 | $500 | 2 tools + cross-project reporting + retro automation |
| Premium | $5,000 | $500 | Full suite + exec reports + resource leveling |

## Deliverables
- Daily standup prep (per team member: yesterday / today / blockers pulled from commits + tickets + Slack)
- Automated chase emails for stale tickets
- Deadline slippage detection (estimates vs actuals)
- Weekly status report (per project)
- Monthly retrospective draft
- Blocked-task escalation to manager
- Cross-team dependency tracking
- Sprint health scoring

## Integrations Supported
- PM: Linear, Jira, Asana, ClickUp, Notion, GitHub Projects, Monday
- Chat: Slack, Teams, Discord
- Git: GitHub, GitLab, Bitbucket
- Calendar: Google Cal, Outlook
- Docs: Notion, Confluence, Google Docs

## Client Requirements
- Read/write API tokens for PM tool
- Team roster with role + manager
- Project list with goals + target dates
- Slack/Teams channel for standup bot
- 30-min per team member for voice sample (for chase tone)

## Setup Timeline
| Day | Milestone |
|-----|-----------|
| 0 | Kickoff + access + roster |
| 1-4 | Wire integrations + build team model |
| 5-7 | Shadow run 1 sprint (no sends) |
| 8-10 | Supervised mode (drafts go to PM for approval) |
| 11-14 | Autonomous mode with chase cadence tuning |
| 15 | Full launch |

## Success Metrics
- On-time ticket completion (vs baseline)
- Standup prep time saved (per person)
- Blocked-task median time-to-unblock
- Manager hours saved/week
- Team satisfaction (quarterly pulse)

## Why Managed Agent
- Multi-hour session = tracks standup → sprint retro across days
- Approval gates on any action that might embarrass a team member publicly
- Always-on = catches blockers in real time, not at Monday standup
- Memory = remembers who owns what, who's on PTO, who just shipped something hard
