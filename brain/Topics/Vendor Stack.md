---
type: topic
name: "Vendor Stack"
tags:
  - topic
  - infrastructure
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Vendor Stack

## Summary
Third-party services AgentNexLiFy depends on.

| Vendor | Role |
|---|---|
| [[Anthropic]] | Claude API + Managed Agents runtime |
| Supabase | Postgres + RLS + pgvector (org [[VoltOps]]) |
| Railway | Backend host |
| Vercel | Frontend + marketing host |
| Resend | Transactional email |
| Twilio | SMS / voice |
| Stripe | Payments / subscriptions |
| Cloudflare | Browser Rendering (website crawl) |
| Vapi / Retell | Voice-AI partners (Vapi primary, Retell backup) |

## Related
- [[AgentNexLiFy Platform]] · [[VoltOps]] · [[SSE not WebSockets]]

## Provenance
- [[dev-knowledge-architecture-decisions]] · [[repo-agentnexlify-claude-md]] · [[docs-deployment-surfaces]]
