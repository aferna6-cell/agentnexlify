# Audit — /demo experience pre-outreach check (2026-07-09)

Outreach recipients land on /demo; verified it survives the June changes
(kill-trial, repricing, widget updates) before any send.

## Verdict: PASS, no changes needed

- `frontend/src/pages/DemoExperience.jsx` is a fully client-side scripted
  simulation (tabbed workforce/frontdesk/leads/automations/calendar demos).
  Zero live API calls besides analytics `trackEvent` — backend changes cannot
  break it.
- CTA builds `/signup?plan=chatbot&from=demo` and forwards `ref`, `vertical`,
  and `business` URL params (DemoExperience.jsx:484-493) — attribution from
  outreach links survives through to signup, which was E2E-verified against
  live prod today (register → login → Stripe checkout session).
- No stale plan pricing in the page (dollar figures are scripted demo content:
  invoices, appointment values). No free-trial language (kill-trial safe).
- Vertical-aware: `?type=` maps industry keywords to the most relevant demo
  tab (typeToDefaultTab), so per-vertical outreach links open on the right
  scenario, e.g. /demo?type=plumbing opens the leads tab.

## For the outreach send (owner)

Use links of the form `https://www.agentnexlify.com/demo?type=<vertical>&ref=<code>`
so the demo opens on the right tab and attribution carries into signup.
