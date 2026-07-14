---
type: company
name: "Instantly"
tags:
  - company
  - vendor
  - outreach
source_status: source-backed
sensitivity: normal
last_verified: 2026-07-13
---

# Instantly

## What it is
Cold-email sending platform (instantly.ai). AgentNexLiFy's outbound vendor for the
[[Cold Outreach Engine]]. Provides warmed sending inboxes, campaign scheduling, email
verification, and a lead database ("Lead Finder" / Supersearch).

## Account facts (2026-07-13)
- Org id `ff3dbb03-7d07-4456-993f-1390cfbaaab7`. API is v2, Bearer auth.
- **9 warmed sending inboxes** across getagentnexlify.com / tryagentnexlify.com / agentnexlifyhq.com
  (aidan / louis / niko). Per-inbox daily cap **server-enforced at 20**.
- **Lead Finder is on the free tier** (`plan_id_leadfinder: pid_free`) → Supersearch not usable.
  That's why sourcing goes through Google Places instead.
- Email verification: ~0.25 credits each; ~900 credits available.

## How we use it
- Campaigns created as DRAFT, leads verified, then activated. Only `activate` sends real email.
- `insert_unsubscribe_header` on + `stop_on_reply` on for CAN-SPAM + hygiene.
- The Instantly MCP (`mcp-servers/instantly/`) wraps these operations for agent use.

## Vendor stack context
Sits alongside [[Resend]] (transactional email), Twilio (SMS/voice), Stripe (payments) in the
[[Vendor Stack]]. Instantly is outbound cold email only — not tenant-facing.

## Related
- [[Cold Outreach Engine]] · [[AgentNexLiFy]] · [[Vendor Stack]]

## Provenance
- This session (2026-07-13); Instantly v2 API responses.
