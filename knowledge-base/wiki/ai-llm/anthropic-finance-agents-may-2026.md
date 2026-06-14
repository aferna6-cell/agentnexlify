---
title: "Anthropic ships 10 finance agent templates and Office 365 add-ins May 2026"
category: ai-llm
tags: [anthropic, managed-agents, claude-cowork, finance, microsoft-365, mcp, opus-4-7, vals-ai]
sources:
  - url: https://www.anthropic.com/news/finance-agents
    title: "Agents for financial services and insurance"
    fetched: 2026-05-05
created: 2026-05-05
updated: 2026-05-05
summary: "Anthropic shipped 10 finance agent templates as Claude Cowork plugins, Claude Code plugins, and Managed Agents cookbooks, plus Excel/PowerPoint/Word add-ins (Outlook coming) and 8 new connectors including Moody's MCP app."
---

Anthropic announced 10 finance agent templates on May 5, 2026, packaged three ways: as plugins in Claude Cowork, as plugins in Claude Code, and as cookbook templates for Claude Managed Agents. Each template bundles three things — skills (instructions plus domain knowledge), connectors (governed data access), and subagents (Claude models invoked for sub-tasks like comparables selection or methodology checks). Opus 4.7 anchors the announcement: 64.37% on Vals AI's Finance Agent benchmark, called out as state-of-the-art on financial tasks. See [[anthropic-managed-agents]] for the runtime, [[claude-opus-4-7]] for the model, and [[anthropic-mcp-2026-roadmap]] for the connector standard.

The 10 templates split into research/client coverage and finance/operations. Research and coverage: Pitch builder (target lists, comparables, pitchbook drafts), Meeting preparer (client and counterparty briefs), Earnings reviewer (transcripts and filings, model updates, thesis flags), Model builder (financial models from filings and analyst inputs), Market researcher (sector tracking, news synthesis, broker research). Finance and operations: Valuation reviewer (comps, methodology, firm review standards), General ledger reconciler (GL accounts, NAV calculations against books of record), Month-end closer (close checklist, journal entries, close reports), Statement auditor (consistency, completeness, audit-readiness), KYC screener (entity files, source documents, escalation packaging).

Microsoft 365 add-ins are the second half of the announcement. Excel for financial modeling, formula auditing, sensitivity analysis. PowerPoint for decks that update when underlying numbers change. Word for credit-memo edits against firm templates. Outlook (coming soon) as a chief-of-staff that triages inbox, schedules meetings, drafts in voice. Context carries between apps — an analyst starting a model in Excel does not re-explain when work moves to PowerPoint. Claude Cowork adds Dispatch: text or voice task assignment for work to continue on local files while the analyst is away from the desk.

Connector ecosystem grew by 8: Dun and Bradstreet (verified business identity, D-U-N-S Number), Fiscal AI (real-time fundamentals on public equities), Financial Modeling Prep (quotes, fundamentals, statements, filings, transcripts across equities, ETFs, crypto, forex, commodities), Guidepoint (100,000+ compliance-reviewed expert interview transcripts with verbatim excerpts), IBISWorld (industry-level revenue, ratios, risk scores, cost structures, forecasts), SS&C IntraLinks (DealCentre data rooms for diligence Q&A and deal-activity tracking), Third Bridge (primary-source expert interviews on companies, sectors, value chains), Verisk (property, casualty, specialty insurance data for underwriting, claims, risk). Moody's separately launched an MCP app (different from a connector) — surfaces interactive UI inside Claude with proprietary credit ratings on 600M+ public and private companies.

Customer quotes name FIS (AML investigations from days to minutes, with credit decisioning, fraud, deposit-retention agents to follow), Carlyle (firm-wide adoption across investing, operations, portfolio management), Walleye Capital (100% of 400 employees on Claude Code), and a hedge fund using Claude for Excel powered by Opus 4.6 for due diligence and modeling. The pattern across testimonials: agents stay in-loop — humans review, iterate, approve before client-facing or filed work. Compliance and engineering teams inspect every tool call and decision through the Claude Console audit log.

## Key Concepts

- **Agent template** — reference architecture packaging skills, connectors, and subagents; a firm adapts it to its own modeling conventions and approval flows
- **Three deployment surfaces** — Claude Cowork plugin (alongside the analyst), Claude Code plugin (alongside the engineer), Managed Agents cookbook (autonomous on the Claude Platform)
- **MCP app vs connector** — connectors give governed real-time data access; MCP apps embed a provider's interactive UI directly inside Claude (Moody's is the launch example)
- **Claude for Excel** — add-in that builds models from filings and feeds, audits formulas across linked workbooks, runs sensitivity analyses; carries context to PowerPoint and Word
- **Vals AI Finance Agent benchmark** — public benchmark for finance-domain agent performance; Opus 4.7 leads at 64.37%
- **Dispatch (Claude Cowork)** — text or voice task assignment that lets Claude continue working on local files while the analyst is away

## Related Articles

- [[anthropic-managed-agents]] — runtime that hosts the Managed Agent variant of these templates
- [[claude-opus-4-7]] — anchor model for the announcement, 64.37% Vals AI Finance benchmark
- [[anthropic-mcp-2026-roadmap]] — MCP connector and app pattern context
- [[claude-cowork]] — desktop plugin host for the in-Office workflow
- [[anthropic-economic-index-learning-curves-march-2026]] — the API automation patterns for finance map to these templates

## Relevance to AgentNexLiFy

AgentNexLiFy's managed-agents roadmap maps directly to this announcement. The template anatomy — skills + connectors + subagents — matches the project's `managed_agents_registry.py` design. Three of the 10 finance templates have small-business analogs that should be on the AgentNexLiFy roadmap: Meeting preparer (pre-call briefs for SMB owners), Statement auditor (monthly P&L review for owner-operators), KYC screener (new-customer onboarding for regulated verticals like contractors with bond requirements). The MCP app pattern (Moody's) is more interesting than the connector pattern — it surfaces vendor UI inside Claude, which is the eventual model for AgentNexLiFy verticals to ship widget-embedded UIs. Pricing reference: enterprise finance customers run Opus 4.7 at $5/$25 per million tokens, AgentNexLiFy SMB tenants need Haiku/Sonnet tier economics. Don't try to copy the finance template prompts wholesale; rebuild them on Sonnet 4.6 with Haiku 4.5 cleanup steps and use the structure as a planning artifact.
