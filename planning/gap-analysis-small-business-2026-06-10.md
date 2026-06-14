# Gap Analysis — "Real Asset for a Small Business" (2026-06-10)

Question: an owner pays $99–250/mo — what stops AgentNexLiFy from feeling like
real staff instead of a clever demo? Graded against what a hired human
office manager would do, using MTOptions (informal beta, non-technical owner)
as the reference customer. Each gap: evidence → fix → effort (S/M/L).

## Fixed in this session

### G1. Approvals rotted silently (trust killer #1) — FIXED
A draft needing approval sat invisible until the owner happened to open the
dashboard. To the customer on the other end, the "AI staff" just went quiet.
**Fix shipped:** `os_approval_notify.py` — owner gets an email the moment a
draft parks in pending_approval (pending count, what it is, one-click review
link; 30-min throttle so bursts don't flood). Wired into the thread runner as
a background task; 4 tests.

## Open gaps, ranked by what breaks trust first

### G2. The owner never sees what the AI was worth ($) — HIGHEST OPEN [M]
Daily briefing (SMS, opt-in) and monthly report (autopilot-only) exist, but
nothing tells every paying owner weekly, in dollars-adjacent plain English:
"your AI handled 14 conversations, captured 9 leads, booked 3 appointments,
sent 2 invoices worth $1,840." Retention lives or dies here — it's the
renewal argument written by the product itself.
**Fix:** weekly value digest email for ALL paying tenants (reuse
`daily_briefing._build_briefing` aggregation + email template; schedule in
`scheduled_jobs`). ~Half day. Do before MTOptions' second week.

### G3. Phone calls — the #1 small-business channel — don't exist [L]
Missed-call textback exists (`textback_enabled`), but competitors (Phonely,
Toma, Drillbit) answer the phone. For trades/medical verticals, phone IS the
business. Textback is a good bridge; voice is a roadmap bet.
**Fix now:** make textback prominent in onboarding (it's buried in settings).
**Fix later:** Twilio Voice + streaming reply as a `professional`-tier
feature. Decide after beta feedback — don't build ahead of demand.

### G4. "Embed one line on your website" assumes they can [M]
Non-technical owners on Wix/Squarespace/GoDaddy often can't edit raw HTML, or
have no site at all. The hosted business page (`/biz/:slug`) exists but isn't
positioned as "no website? we ARE your website."
**Fix:** (a) platform-specific install cards in the wizard embed step +
/help (Wix/Squarespace/GoDaddy/WordPress each have a documented snippet
flow); (b) "no website" path in onboarding that leads with the hosted page +
widget pre-installed. (a) is copy, ~2 hrs; (b) ~1 day.

### G5. Three different price stories on three surfaces [S — needs OWNER decision]
Canonical (CLAUDE.md): growth $99 / autopilot $150 / professional $250 /
enterprise $899. BillingPage table: Professional $150, Enterprise $250, no
autopilot row. Home FAQ: a third variant. An owner comparing checkout vs
marketing page sees different numbers — at the exact moment they're deciding
to pay. **Fix:** owner picks the canonical set; then one pass aligns
BillingPage PLANS, Home pricing section + FAQ, HelpPage compare. Code is
trivial; the decision is the blocker (flagged to owner 2026-06-10).

### G6. After-hours auto-send is all-or-nothing [M]
`os_auto_send_enabled` is a single global toggle. A 2 AM widget question
waits for morning approval unless the owner trusts EVERYTHING to auto-send.
Human staff get standing instructions ("answer FAQs freely, ask me before
quoting"). **Fix:** per-agent or per-channel auto-send rules (schema:
JSONB rules column or per-agent flags; engine gate already centralizes in
`resolve_deliverable_status`). ~1–2 days. Validate demand with beta first.

### G7. The AI can't do anything it wasn't asked to do [M/L]
Everything is reactive (owner prompt or widget visitor). A real staffer
notices: "3 leads went cold this week — want me to follow up?" The pieces
exist (scheduled jobs, graph memory, backlog) but no proactive suggestion
loop feeds the OS backlog. **Fix:** nightly per-tenant "opportunities" job
writing suggestion cards to the OS backlog (NOT auto-executing — suggestions
only, approval flow already exists). Start with 2 deterministic rules:
cold-lead nudge + unpaid-invoice reminder suggestion. ~2 days.

### G8. Vertical depth is template-thin beyond the top 5 [ongoing]
27 industries in signup; 5 have tailored starters (FirstRunStarters), the
rest fall to `_default`. The moat thesis is vertical knowledge per tenant.
**Fix:** per-beta-vertical deepening — MTOptions' industry first: starters,
seeded FAQs, agent prompt language. ~2 hrs per vertical, compounding.

## What's NOT a gap (verified, don't rebuild)
Lead capture + booking + invoicing through chat; knowledge-graph long-term
memory with owner-visible panel + Forget; mobile OS; GDPR deletion + cookie
consent + DPA; dunning + recovery + fraud pause; review requests; referral
links; daily briefing; uptime/load/billing test evidence (rubric 221/262).

## Sequence recommendation
1. G2 weekly value digest (before MTOptions week 2)
2. G5 pricing decision (owner) + alignment pass (same day as decision)
3. G4a platform install cards (copy-level, quick)
4. G7 proactive suggestions v1 (after first beta feedback)
5. G6 granular auto-send (when a beta tenant asks for it — they will)
6. G3 voice (decision point after beta; buy-vs-build Twilio)
