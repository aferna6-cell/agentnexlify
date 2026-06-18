# Audit: Signup to First Value

Date: 2026-06-18
Scope: the path a brand-new customer walks from clicking "Get Started" to the
first moment AgentNexLiFy does something useful for them. Triggered by the
outreach push (cold email will drive cold signups who have low patience).

This is a findings report, not a change. Fixes belong in a separate session
(per the "don't fix and audit in the same session" rule).

## The path today
1. `/signup` (`SignupPage.jsx`) collects account + plan, captures `?ref` for
   attribution, redirects to Stripe Checkout.
2. Checkout charges immediately (no trial, #322) and returns to
   `/dashboard?checkout_success=1&session_id=...` (#325 fixed the old dead
   `/billing/success` logout).
3. `RequirePaid.jsx` polls `/me` on the Stripe return until `plan_status` is
   active, then renders the app.
4. Onboarding wizard (`OnboardingWizardPage.jsx`) runs 6 steps: Business,
   Auto-KB, Services, Knowledge Base, Customize, Embed.
5. First value: `AgentOS.jsx` with `FirstRunStarters` suggested prompts, and/or
   the chat widget embedded on their site.

## What is already good
- No logout after checkout; lands signed in on the dashboard (#325).
- Welcome email is clearly branded and gives a first action (merged today).
- `FirstRunStarters` gives a non-empty AgentOS first screen (good empty state).
- Auto-KB step scrapes the business website, so the AI can answer real
  questions quickly without manual data entry.
- Workforce-gated features now show an upgrade prompt instead of a raw error
  (#327).

## Findings (ranked)

### HIGH - 6-step wizard before first value
A cold-signup roofer who just paid hits 6 wizard steps before talking to the AI.
Time-to-first-"aha" is the #1 activation driver. The fastest aha is "ask the AI
something and get a useful answer about MY business," which Auto-KB enables by
step 2.
- Quick win: after Auto-KB completes, offer a "Talk to your AI now" shortcut
  that jumps straight to AgentOS with a pre-filled starter, letting them skip
  ahead and finish Services/Customize/Embed later.
- Files: `OnboardingWizardPage.jsx`, `WizardStepAutoKB.jsx`, `AgentOS.jsx`.

### HIGH - demo-to-signup continuity is lost
A prospect who clicked a personalized `/demo?business=Acme+Roofing` saw a demo
framed for their business, but after signup the wizard does not carry that
context (business name/vertical) forward, so they re-enter it. `?ref` is
captured for attribution but business/vertical are not pre-filled.
- Quick win: carry `business` + `type` from the demo link into signup and
  pre-fill `WizardStepBusiness` so they confirm rather than retype.
- Files: `DemoExperience.jsx` (already sends params), `SignupPage.jsx`,
  `WizardStepBusiness.jsx`.

### MEDIUM - Auto-KB failure has no graceful fallback surfaced
If the website scrape returns little/nothing (no site, JS-only site, scrape
blocked), the AI starts thin and the first interaction underwhelms. Need to
confirm the wizard clearly offers a manual FAQ path when Auto-KB comes back
empty, rather than silently proceeding.
- Action: verify `WizardStepAutoKB.jsx` empty-result UX; add a "we could not
  read your site, add a few FAQs" branch if missing.

### MEDIUM - no in-product "first lead captured" moment
The strongest activation signal is the customer seeing the AI capture a real
lead. Lead alerts exist (#317) but there is no first-run nudge that says "add
the widget to your site so your AI starts catching leads tonight," tied to the
Embed step.
- Quick win: make the Embed step end on a concrete "you will get an email the
  moment your AI captures a lead" promise (now true via lead alerts).

### LOW - email verification timing (confirm)
Confirm whether email verification gates first app use. If a cold signup must
verify email before reaching value, that is avoidable friction; verification can
run in parallel rather than as a hard gate.
- Action: check the register flow for a verification gate.

### LOW - mobile wizard
Many local-business owners sign up on a phone. Confirm the 6-step wizard +
AgentOS first screen are usable on mobile (the dashboard is desktop-first).

## Recommended sequence (separate build session)
1. Demo-to-signup context carry (HIGH, small) - highest leverage for the
   outreach funnel specifically.
2. "Talk to your AI now" shortcut after Auto-KB (HIGH, small).
3. Auto-KB empty-result fallback (MEDIUM).
4. Embed-step "first lead" promise (MEDIUM, copy).
5. Verify email-gate + mobile pass (LOW).

## Note
Findings are grounded in file structure, not a live run-through. A real
end-to-end signup on the deployed app (one test account) would confirm exact
step order, the Auto-KB empty path, and the verification gate before building.
