# Ideas — Run 87 (2026-07-10-pm)

## Evidence Digest

Morning-digest-2026-07-10 executed all three run_87_mandate items ahead of schedule:
- ✅ `ops/credential-rotation-schedule.md` created
- ✅ Step 9E added to `.claude/skills/nightly-commit-review/SKILL.md`
- ✅ Lead Source Analytics GH issue created with `ai-ready` label

Automation pipeline still broken: AUTOPILOT_GH_TOKEN expired (GH #399, CRITICAL), ANTHROPIC_API_KEY missing from GitHub Actions (GH #403, CRITICAL). Issue-to-pr-loop: 30+ consecutive failures since 2026-07-04. KB autopopulate: blocked.

Production stats: 7 real leads, 0 real bookings, 3 paying tenants (MTOptions, 914 Exterior, Keys Koffee), 0 new signups in 16 days. `0e0ee00` turned booking ON by default — but only for NEW onboarding. Existing tenants may still have `booking_enabled=false`.

Weekly funnel report (3596009): service ships, already wired to automation loop in main.py line 344 — no new wiring needed.

10 stale draft PRs (age 1–18+ days): #325 checkout fixes, #327 agent OS upgrade prompt, #328 retention save-offer, #86 hooks.

---

### Idea 1: Booking Enabled Audit for Real Tenants
**Evidence:** 0 real bookings despite 7 leads and booking nudge shipped 2026-06-23. `0e0ee00` (2026-07-09) set `booking_enabled=true` as default for NEW onboarding only. MTOptions, 914 Exterior, and Keys Koffee onboarded before this change — they retain their original `booking_enabled` value. If any have `booking_enabled=false`, the booking feature is silently off for all paying customers.
**Action:** Nightly queries `widget_configs` table for real tenant slugs (exclude demo tenants), reports `booking_enabled` status, files a GH issue with exact SQL UPDATE statement if any real tenant has `booking_enabled=false`.
**Impact:** Could unlock the first real booking. If all 3 tenants have booking off, fixing takes 1 Supabase UPDATE per tenant. Direct revenue.
**Category:** customer_value / code_health

---

### Idea 2: Draft PR Triage — Close or Merge Stale Drafts
**Evidence:** 10 open draft PRs including several 18+ days old. PR #86 (hooks audit fix), #325 (Stripe Link kill + conversion), #327 (agent OS 402 prompt), #328 (retention save-offer), #341 (KB drift sweep). These age every day without review, accumulating merge-conflict risk.
**Action:** Nightly generates a triage comment on each stale draft PR (>7 days): lists blockers, asks for merge decision or close. Does NOT auto-merge. Creates one GH issue labeling 5 most-impactful for human review this week.
**Impact:** Reduces technical debt accumulation. Surfaces #325 (checkout conversion fix) which is directly revenue-relevant.
**Category:** workflow / code_health

---

### Idea 3: Referral Reward Pre-Gate Diagnostic
**Evidence:** GH #407 HIGH — referral reward webhook (#372) solid (20 tests green, kill-switch in place) but blocked on: (1) migration 162 applied in prod, (2) Stripe staging smoke. Both checks are manual today. The feature is gated off (REFERRAL_REWARD_ENABLED=0) but ready to flip.
**Action:** Add a nightly diagnostic: read migration files to confirm migration 162 exists; check whether REFERRAL_REWARD_ENABLED is set in any deployment config; log result in nightly report. Surfaces as "ready to flip" signal when both conditions are met.
**Impact:** Reduces the time-to-flip for a shipped revenue feature from 30-minute manual check to auto-confirmed. Referral reward = growth multiplier.
**Category:** workflow / operational

---

### Idea 4: landing-page-v2 Widget Retirement Decision
**Evidence:** GH #408 MEDIUM — `8b1e44b` (2026-07-04) fixed widget drift in `landing-page-v2/widget/`. CLAUDE.md says `landing-page-v2/` is legacy do-not-touch (confirmed 2026-06-23). Two options: (1) delete the file entirely and update CLAUDE.md to remove as concern; (2) document as intentionally maintained exception. The nightly has been flagging this for multiple runs. Leaving it ambiguous costs nightly attention every cycle.
**Action:** Nightly files a decision request on GH #408 with exact options: A) delete `landing-page-v2/widget/agentnexlify-widget.js` (removes the concern permanently) or B) add a `<!-- drift-ok -->` comment in check_project_invariants.py to exclude it. Owner picks one.
**Impact:** Permanently removes a recurring nightly false-alarm. Reduces governance noise.
**Category:** code_health / operational

---

### Idea 5: ANTHROPIC_API_KEY Blockage Escalation
**Evidence:** GH #403 (CRITICAL, open) — ANTHROPIC_API_KEY not set in GitHub Actions secrets blocks KB autopopulate + autopilot. Present in morning digest priority list, 5+ days stalled. All autonomous AI-powered workflows are dead without it.
**Action:** Add a dedicated check to the nightly routine (Step 9F): attempt to detect whether GH Actions workflows that depend on ANTHROPIC_API_KEY have had any successful run since the last 7 days. If not, comment on GH #403 with escalating urgency (Day 1: note, Day 3: HIGH, Day 7: CRITICAL with full manual procedure embedded).
**Impact:** Converts a static GH issue into an escalating daily reminder. Forces visibility if credentials aren't rotated.
**Category:** operational
