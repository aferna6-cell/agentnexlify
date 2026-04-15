# AgentNexLiFy Managed Agents — Client Product Line

Six sellable AI agents deployed on Anthropic Claude Managed Agents infrastructure. Cloud-hosted, always-on, no servers for the client to maintain.

## Positioning
**"AI employees for small businesses. No code. No hiring. No overhead."**

Target buyers: same SMB segment as our core product (salons, plumbers, dentists, contractors, real estate, legal, accounting). Sell as addon or standalone.

## The 6 Agents

| # | Agent | Setup | Monthly | Positioning |
|---|-------|-------|---------|-------------|
| 1 | [Client Onboarding](client-onboarding/SPEC.md) | $1,500-3,000 | $500 | Welcome new customers, collect docs, trigger workflows |
| 2 | [Executive Report](executive-report/SPEC.md) | $3,000 | $500 | Weekly KPI digest from multiple data sources |
| 3 | [Customer Support](customer-support/SPEC.md) | $2,000-5,000 | $500 | 24/7 tier-1 response across email + chat + SMS |
| 4 | [Document Processor](document-processor/SPEC.md) | $2,000-4,000 | $500 | Invoice/contract/form intake → structured data |
| 5 | [Project Management](project-management/SPEC.md) | $2,500-5,000 | $500 | Task triage, status updates, deadline tracking |
| 6 | [Content Repurposer](content-repurposer/SPEC.md) | $2,000-4,000 | $500 | Blog → social, video → posts, newsletter → tweets |

## Claude Managed Agents — Why This Infrastructure

Four building blocks per the Anthropic spec:
1. **Agent** — instructions + tool allowlist (system prompt)
2. **Environment** — pre-installed software + credentials (the workspace)
3. **Session** — multi-hour running conversation with memory + files
4. **Events** — input messages, output messages, approval gates before sensitive actions

Benefit over local/Cowork: runs on Anthropic cloud, no client infra, uptime handled by Anthropic, SOC 2 inherited.

## Standard Package Components (all 6 agents)
- Initial spec + kickoff call
- Cloud agent provisioning (Claude Managed Agents)
- Integration wiring (Gmail, Slack, Stripe, Supabase, etc. via MCP)
- Approval gates on destructive actions (send email, charge card, delete record)
- 30-day post-launch iteration
- Monthly retainer: monitoring, prompt tuning, integration adds

## Pricing Notes
- Setup = one-time implementation fee
- Monthly = retainer covering monitoring + iteration + bug fixes + up to 2 small feature adds/month
- Setup ranges reflect integration complexity — bottom of range = simple (single tool), top = complex (5+ integrations)
- Volume discount: 3+ agents same client → 15% off setup each, $1,200/mo bundled retainer

## Sales Process
1. Discovery call (30 min, free) — map client's repeating pain
2. Match to 1-2 of the 6 agents — scope setup fee from range
3. Proposal + contract (1-page each)
4. Deposit (50% setup) + kickoff
5. Build + QA (timeline per agent SPEC)
6. Launch + handoff to retainer

## Target Economics Per Agent
- Setup margin: 70-85% (mostly prompt engineering + integration glue)
- Retainer margin: 60-75% (ongoing cost = Claude API usage + 2-4 hrs/mo human)
- Break-even: month 1 on setup alone
- LTV: 18-36 months avg retention, $6k-18k monthly recurring per client after 3 agents

## Upsell Path
1. Start client with 1 agent from core product (AgentNexLiFy widget)
2. Offer onboarding agent during 60-day check-in
3. Add 2nd agent at month 4-6 based on observed pain
4. Bundle 3+ at annual renewal

## Cross-refs
- `.claude/skills/mcp-builder/SKILL.md` — for wiring new integrations
- `.claude/rules/claude-code-security.md` — for managed agent credentialing rules
- `backend/routers/` — existing tenant context (these agents scope per `client_id`)
- `knowledge-base/wiki/ai-llm/` — LLM pattern library
