# Council — Onboarding / Integration Strategy for SMB (<$500k, many <$100k)

**Date:** 2026-06-25. **Method:** LLM Council, 5 independent seats (SMB owner, integrations
architect, GTM strategist, product/UX, risk/security) + chairman synthesis.
**Question:** product = AI Front Desk ($19.99 inbound widget→CRM/score/follow-ups) + AI
Workforce ($99.99, 8 department-head agents). How do we integrate into a local business's
systems (inboxes, data, files, QuickBooks, vendors, social) and make setup seamless,
valuable, and digestible so the owner sees value fast? Where do we improve / what's a concern?

---

## Chairman verdict — the 4 moves all seats converged on

1. **Lead with "never miss a lead" (missed-call text-back + web capture), NOT "AI chat widget."**
   The website-visitor problem is an abstraction to a roofer/salon; the phone ringing while
   they're busy is felt money. Missed-call text-back is also near-zero setup (forward a number)
   and self-demonstrates in days. Reframe the entry tier around capture-everywhere.

2. **Sell ONE assistant ("your AI office manager"), not "8 bots / orchestrator."**
   The 8-agent framing reads as enterprise/complex at the point of sale and reactivates setup
   anxiety. Reveal the 8 as "your team" INSIDE the product (progressive disclosure, attribution
   tags like "— from your Collections assistant"). Daily use = one inbox.

3. **Activate only on things WE control; defer every customer-held OAuth.**
   Do-first (high value / low friction): widget script tag, Twilio SMS + missed-call text-back
   (we provision the number — owner connects nothing), Google Calendar (single consent), Stripe
   payment links. Defer to post-activation upsell: Gmail/M365 send, Google Business Profile,
   Meta/Facebook DMs, QuickBooks. Never gate signup→value on an OAuth screen.

4. **Speak in money, never "score."** Dashboard top cards = Leads captured, Estimated pipeline
   ($ = leads × avg job value captured in onboarding), Missed leads recovered. Reframe the
   conversation "score" as a temperature (Ready to book 🔥 / Just looking 👀 / Spam) and
   "suggested follow-ups" as "Do this next to win the job" + one-tap [Text them back].

## Integration tiers (the explicit answer to "connect everything")
- **DO FIRST (we control, no OAuth):** widget, Twilio text-back, Stripe links, single Google Calendar.
- **HIGH value / HIGH friction (sequence, don't gate):** email send (use Resend on our domain to
  dodge Gmail restricted-scope CASA review + M365 admin consent), Google Business Profile
  (allow-listed API), Meta DMs (app review + business verification — start the review clock NOW;
  it's wall-clock, not eng-effort).
- **LOW value for this segment — drop/defer:** deep QuickBooks two-way sync, HubSpot sync,
  "vendor management" (this segment has no vendor systems). Many do finances manually.
- **QuickBooks 80/20:** do NOT sync the ledger. Invoicing agent drafts → owner approves →
  send + collect via Stripe link. Offer read-only CSV/QBO import of customers + open invoices for
  the minority who want it. Never write back to the books (tax-error liability).

## Immediate improvements (ranked, impact × effort)
1. **Missed-call text-back live in <5 min, we provision the number** — highest impact, low effort. *(Prereq: see concerns #3/#5 — never run in prod yet.)*
2. **URL-crawl auto-config + live "it already knows my business" bot preview** — aha in <60s, kills the "configure it" wall.
3. **Money-language dashboard** (pipeline $ + recovered-leads cards; score→temperature).
4. **Platform-aware widget installer** (auto-detect Wix/Squarespace/GoDaddy/WordPress → deep-link
   or "email the snippet to my web person") + live "widget detected ✅" health check.
5. **Hosted micro-page + QR for the no-website segment** (large slice) — converts a dead-end TTV path.
6. **CSV import with column-mapping + dedupe PREVIEW (approve, never auto-merge).**
7. **Free 20-min concierge setup call as the standard close** (doubles as demo + activation
   guarantee; optional one-time "Done-For-You Launch" $199–299 for tier-2 who'd rather pay than fiddle).
8. **Onboarding wizard that reveals value each step:** name+URL → avg job value + top service →
   pick #1 time-sink (triggers a live sample task) → connect the ONE thing for that goal → confirm.

## Concerns / must-fix BEFORE pushing "seamless all-your-systems integration" (Seat 5, code-verified)
1. **TCPA / CAN-SPAM guardrails are missing in the SMS path.** `backend/services/os_actions/sms.py`
   has no STOP/HELP/opt-out handling, no consent ledger, no quiet-hours, no per-day cap (grep = 0
   hits). TCPA damages are $500–$1,500 **per text**. This is legal-existential before any scaled
   sending. MUST add: opt-out keyword handling on the inbound webhook, a consent/opt-out table
   checked before every send, quiet hours, per-tenant rate caps, CAN-SPAM footer (already added to
   cold sequences). #1 priority.
2. **Tenant isolation on financial/PII tables** — we shipped `client_id`/`tenant_id` isolation bugs
   3+ times (and fixed plan-gating + a plan-check constraint THIS week). Do not hold QuickBooks/
   financial data until RLS isolation is provably enforced on every financial table.
3. **Missed-call text-back is built but has NEVER run in prod (0 sends ever).** Verify the full
   chain (call → voicemail → transcription webhook → draft → approval → delivered SMS from the
   right number, 10DLC registered) before demoing or selling it.
4. **"Clean my data" is a trust landmine.** An AI that auto-merges/dedupes a customer list or
   categorizes QuickBooks will collapse two real "John Smith"s or mis-file a transaction the owner
   finds in April — and blames us. Boundary: **propose-only, per-record approval, immutable audit
   log, one-click rollback. Never mutate.**
5. **Silent integration failure = silent churn.** OAuth tokens lapse on password change; cron
   errors are swallowed (bare `except: logger.warning` in voice_recovery.py); widget mis-paste/CSP
   block → owner sees zero leads and assumes the product is dead. Need active integration health
   checks that ALERT the owner (red/green connection status, "reconnect your Google account"
   emails, a test-send/test-widget-fire verification at setup).

## Packaging resolution
Keep the two tiers ($19.99 / $99.99, month-to-month — a real wedge vs GHL/Podium/Birdeye/Thryv's
$300+ and annual contracts), but **rename around outcomes** ("never miss a lead" vs "your AI office
manager") and make setup free/concierge. Win on price + month-to-month + time-to-value +
simplicity of setup — do NOT out-promise Podium's human onboarding; out-SIMPLIFY it (one action:
forward a number OR paste one line). Week-one closer = a real captured lead pushed as a
notification: "We just texted back Jane (missed call 2:14pm) — she wants a quote."

## Disagreements logged
- Seat 1 finds the Front Desk/Workforce split confusing ("which one am I?"); Seat 3 keeps two
  tiers. Resolution: keep two SKUs, reframe names to outcomes, entry tier = capture not "chat."
- Charging for setup: Seat 3 says free concierge wins trust; optional paid DFY for tier-2. Adopted.

## Cross-refs
- `docs/dev-knowledge/website-surface-map.md` (live site = frontend/, widget greeting in DB)
- `backend/services/os_actions/sms.py` (TCPA gap), `backend/services/voice_recovery.py` (text-back, untested)
- `docs/ops/runbook-mtoptions-textback-activation.md` (text-back activation)
- `.claude/rules/schema-discipline.md` (client_id isolation — repeated bug class)
