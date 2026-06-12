# Architecture Health Report — AgentNexLiFy — 2026-06-12

Weekly structural review focused on the last ~48h of commits (voice/calls
split, demo sandbox, N+1 batching, dual scheduled trees, vertical depth
passes). AUDIT ONLY — fixes tracked separately. Produced by the
improve-architecture pass; CRITICAL #1 and the S-effort items were fixed
same-day in the demo-hardening PR (see git log); remaining items are open.

## CRITICAL

- [x] **Demo role can send real SMS via unguarded `twilio_service.send_sms`.** Effort: M
  `send_sms()` had no `is_demo_tenant` check; `widget_chat.py` "talk to human"
  handoff fired a real SMS for demo visitors while the twin email was
  suppressed. FIXED same-day: guard added inside `send_sms` (optional
  `tenant_id` param, success-shaped no-op), tenant context threaded at the 7
  demo-reachable call sites (widget_chat handoff, sms.py x2, leads.py,
  invoices.py x2, sequences.py). Staged adoption documented in the docstring;
  remaining scheduled-job sites are covered by fake 555 numbers + nightly reset.

- [ ] **Dead duplicate scheduled-jobs tree: `backend/services/automation/scheduled_jobs/` (package).** Effort: M
  The LIVE tree is `automation/scheduled/` (imported via the `scheduled_jobs.py`
  shim). The `scheduled_jobs/` PACKAGE (reviews.py 541 lines, leads, onboarding,
  appointments, invoices, reports, _common) has ZERO external importers — only
  6 self-referential `_common` imports. `scheduled_jobs/reviews.py` is a full
  live-logic duplicate of `scheduled/review_jobs.py`. Half-migration orphan
  (user-rules Rule 8). Fix: confirm zero runtime import, delete the package in
  its own PR (dead-code-sweep skill). Keep the `scheduled_jobs.py` shim.

## HIGH

- [ ] **Demo outbound guard is per-call-site, not a true chokepoint.** Effort: M
  With send_sms now guarded, enumerate remaining non-chokepoint senders
  (Twilio voice dial-out in calls.py, direct httpx/Resend) and route them
  through guarded functions or add the guard. block_demo_role covers the four
  money/destructive routers but not messaging routers — those rely on the
  send-level guards.

- [ ] **`voice_call_summary.py` has no dedicated degradation tests.** Effort: M
  The "never raise into a webhook path" contract is untested in isolation.
  (`voice_twiml.py` escaping got a dedicated test same-day.)

## MEDIUM

- [x] **Stale schema-drift baseline comment** ("post-migration 140" vs live ceiling 144).
  Baseline data itself was current; comment fixed same-day.
- [ ] **Split-brain test layout**: tests/ (68 files) vs backend/tests/ (60) with
  overlapping concerns. No stale patch targets found. Document the split
  (root = integration, backend = unit) or consolidate later — high blast radius.
- [x] **Dead Calendly redirect leftovers in `frontend/src/main.jsx`**
  (CALENDLY_URL const, RedirectExternal fn — orphaned by DemoLoginPage).
  Removed same-day. ComparisonPage keeps its own used copy.

## LOW

- [x] **`voice_twiml._xml_escape` divergence from `html.escape` undocumented.**
  Intentional: XML named entities (&apos;) vs html.escape's numeric &#x27;.
  Comment added same-day so nobody "simplifies" it into a behavior change.
- [ ] **God-class watch list** (>600 lines, none newly bloated; calls.py SHRANK
  1436->918 post-split): widget_chat.py 1206, email_sequences.py 1132,
  invoices.py 1066, onboarding.py 1050, leads.py 980, booking_page.py 941,
  calls.py 918, widget_chat_helpers.py 857, demo_seed.py ~830, auth.py 784,
  rule_engine.py 772, bids.py 732, forms.py 731, widget_lead_helpers.py 732,
  scheduled_jobs_ext.py 711, client_portal.py 690. Rule 9: split before the
  next feature lands in any of them — widget_chat.py and email_sequences.py first.
- [ ] **Vertical-depth files growing by design** (industry_faqs.py 486,
  os_kb_feed.py 408). Healthy — this is the moat. When either crosses 600,
  extract per-vertical data into industry_packs/-style modules.

## Stats
- Files >600 lines: 16 (none newly bloated; calls.py shrank)
- Layer violations found: 0
- Dead code confirmed: scheduled_jobs/ package; main.jsx Calendly leftovers (fixed)
- Schema drift: 0 real; 1 stale comment (fixed)
- Demo security gaps: 1 CRITICAL (fixed same-day) + 1 HIGH chokepoint sweep (open)
- Migrations ceiling: 144, consistent

## Handoff
- CRITICAL #2 (dead scheduled_jobs/ tree) -> dead-code-sweep, own PR.
- HIGH chokepoint sweep + voice_call_summary tests -> next engineering session.
- God-class splits -> next time a feature touches widget_chat.py / email_sequences.py.
