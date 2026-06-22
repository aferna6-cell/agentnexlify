---
type: company
name: "AgentNexLiFy"
aliases:
  - "Agent Nexlify"
  - "AgentNexlify"
tags:
  - company
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# AgentNexLiFy

## Summary
AgentNexLiFy is the business: an AI front-desk and lead-capture SaaS for small service
businesses, built and run solo by [[Aidan Fernandes]]. Multi-tenant from day one. Its
product surface is the [[AgentNexLiFy Platform]] (widget + dashboard) plus [[Agent OS]] (the
conversational agent layer).

## What it does
- Embeddable branded website chat widget that answers routine visitor questions, captures
  leads + conversation context, and books appointments.
- Dashboard for owners to configure services/FAQs/hours/styling and run follow-up workflows
  (CRM, appointments, automations).
- Source: [[repo-agentnexlify-readme]]

## Business model
- Paid plans (repriced 2026-06-15): `chatbot` $19.99/mo (widget/chat only); `agent_os`
  $99.99/mo (full platform). `free` = internal lapsed state, never sold.
- Legacy/grandfathered plans: `growth`, `autopilot`, `professional`, `enterprise`.
- Source: [[repo-agentnexlify-claude-md]] · governed by [[2026-06-15 Plan Repricing]]

## Positioning
- #1 competitor: GoHighLevel ($97–497/mo). Differentiation: widget-first, lower friction,
  per-tenant vertical knowledge base (not generic LLM replies).
- Source: [[repo-agentnexlify-claude-md]]

## Infrastructure
- Backend FastAPI (Railway); frontend React/Vite (Vercel); DB Supabase Postgres w/ RLS
  (org [[VoltOps]]); AI via Anthropic Claude. Source: [[repo-agentnexlify-claude-md]]

## Related
- [[AgentNexLiFy Platform]] · [[Agent OS]] · [[Aidan Fernandes]] · [[VoltOps]]

## Provenance
- [[repo-agentnexlify-readme]] — product definition
- [[repo-agentnexlify-claude-md]] — stack, pricing, positioning
