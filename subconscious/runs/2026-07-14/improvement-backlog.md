# Improvement Backlog — Updated Run 93 (2026-07-14)

## Active (pending nightly implementation)

### HIGH: connector_awareness.py Cross-Tenant Isolation Test [run 93 winner]
- **File**: `backend/tests/test_connector_awareness_isolation.py`
- **Evidence**: commit 7a9047f same-day bug (wrong-dimension filter), commit 45401ec (208L service, 370 tests with no isolation coverage)
- **Autonomy**: AUTONOMOUS-EXECUTABLE (test file only)
- **Effort**: XS (~20 min)
- **Status**: pending_nightly_implementation

---

## Pending Human Action (carry-forward)

### DAY 22 — Keys Koffee business hours [run 92 winner, Day-21 mandate]
- Contact Keys Koffee owner → collect business hours → dashboard → Settings → Booking Hours
- Evidence: booking_enabled=true, 0 business_hours rows confirmed 2026-07-13
- GH #415, comment ID 4963248261
- Days without action: 22

### REFERRAL_REWARD_ENABLED=1 [runs 89-92, 4 consecutive]
- Decide referral copy (1 sentence) → Railway → backend → Variables → REFERRAL_REWARD_ENABLED=1
- Evidence: full stack confirmed, items 3/5/8 code-verified, items 9/10 are product decisions
- GH #413, 4 comments
- If still no action by run 95: switch approach to building item 10 (referral email) then repeat ask

### AUTOPILOT_GH_TOKEN rotation + ANTHROPIC_API_KEY [GH #399 + #403]
- GH Actions → Settings → Secrets → update AUTOPILOT_GH_TOKEN (repo scope) + add ANTHROPIC_API_KEY
- Evidence: 10 days stalled, 40 ai-ready issues queued, KB 69 days dark
- ~15 min total. Unblocks 3 systems.

---

## Parking Lot (future winners, evidence ready)

### HIGH: Referral grant email notification [Idea 1, run 93]
- `backend/services/referral_notification.py` + modify `referral_reward.py:_grant_sync()`
- Build item 10 after comment approach exhausted (4 runs, 0 action)
- Trigger: if GH #413 still 0 human response at run 95 mandate check
- Effort: S (30 min)

### MED: Voice G3 post-call booking confirmation SMS [Idea 3, run 93]
- Wire existing Twilio reminder to fire after voice booking confirmed
- Trigger: after first voice booking occurs in production
- Effort: M

### MED: Tenant notification on new appointment booking [Idea 5, run 93]
- `backend/services/appointment_service.py` → Resend email to tenant on booking
- Trigger: when first real booking is imminent (Keys Koffee hours configured)
- Effort: S

### LOW: Lead Source Analytics Dashboard [run 85]
- GET /api/leads/source-breakdown + BarChart in AnalyticsPage.jsx
- GH issue created with ai-ready label — autopilot loop will pick up once GH #399 resolved
- Pending autonomous execution

---

## Frozen / Retired
- `ai_human_handoff` — FROZEN (governance.json)
- widget drift topic — RETIRED (widget_drift_topic_retired: true in governance.json)
