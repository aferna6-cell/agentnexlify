# Debate Log — Run 90 (2026-07-12)

## Top 3 Ideas Debated

---

## Idea 1: GH Actions Secrets Health-Check Workflow

### Round 1
**Challenge:** "This is meta-fix pattern again. Runs 79-84 were all Steps 9B/9C/9D/9E. We've been
adding monitoring layers for 12 runs. Adding another layer doesn't unstick the CURRENT stall."

**Defend:** The distinction matters: Steps 9B-9E run INSIDE the Claude-dependent nightly workflow.
If ANTHROPIC_API_KEY goes missing from GH Actions, the nightly doesn't run, so Steps 9E can't fire
to detect it. This is a confirmed self-referential blind spot — the watchdog requires the thing it's
watching. A GH Actions workflow using GITHUB_TOKEN (always present, no dependency on monitored
secrets) operates OUTSIDE the Claude stack. It's not another meta-fix; it's a zero-dependency
bootstrapper for the existing monitoring stack. Analogy: Step 9E is a smoke detector that needs
power; this workflow is a battery-backup smoke detector.

### Round 2
**Challenge:** "Can GH Actions actually validate whether an API key is live, not just present?
`secrets.ANTHROPIC_API_KEY != ''` only checks non-empty, not validity. A rotated-but-invalid key
would pass."

**Defend:** Two failure modes to handle: (a) completely missing/empty (#403's case — ANTHROPIC_API_KEY
was never set) and (b) expired (#399's case — token rotated and expired). For case (a), `!= ''`
catches it perfectly — that's the actual failure in #403. For case (b), a one-line curl to
`https://api.anthropic.com/v1/models` with `Authorization: x-api-key $ANTHROPIC_API_KEY` returns
401 on invalid/expired, 200 on valid. Similarly, curl to `https://api.github.com/user` with
AUTOPILOT_GH_TOKEN validates live status. Both calls are lightweight (< 100ms, no Claude needed).
This handles both failure modes.

### Round 3
**Challenge:** "ops/credential-rotation-schedule.md was created as run 84's winner. Doesn't that
already solve proactive credential management?"

**Defend:** `credential-rotation-schedule.md` is a PASSIVE document — it documents rotation cadence
but requires a human to check it proactively. No automation reads it. Step 9E checks days-since-rotation
thresholds, but Step 9E only runs if nightly has Claude API access. The GH Actions health-check is
ACTIVE — it fires automatically regardless of Claude API state. The static doc and the active
workflow are complementary; the doc guides when to rotate, the workflow enforces detection.

**VERDICT: SURVIVES** — 3/3 objections answered with evidence. New mechanism class (not redundant
with existing Steps). Addresses self-referential monitoring gap confirmed across 8 days of stall.

---

## Idea 2: Add Step 9F to nightly SKILL.md — Booking Conversion Tracker

### Round 1
**Challenge:** "Step 9F was explicitly REJECTED in run 88: 'premature — schema unverified,
MCP blocked, hypothesis A unconfirmed.' Both MCP and Supabase access are still unknown. Nothing
has changed on the execution mechanism."

**Defend:** Run 88 rejection was conditional. Run 89 explicitly set the re-enable condition:
'add Step 9F if booking_enabled=true confirmed.' That condition is NOW MET: PR #404 (commit 3596009,
2026-07-11) confirmed MTOptions has 20 booking slots live and 914 Exterior has 22 slots after the
impossible-hours prod bug fix. Hypothesis A (booking_enabled=false for old tenants) is definitively
refuted for 2/3 tenants. The MCP gap is real but Step 9F can use GH API + backend REST endpoint
(curl with service auth) rather than Supabase direct — different mechanism than what ran 88 blocked.

### Round 2
**Challenge:** "The Step 9F mechanism you propose (check GH #412 comments, curl backend API) is
indirect and brittle. GH comment count doesn't tell us if bookings happened. Backend API requires
a service-level auth token that nightly doesn't have."

**Defend:** Phase 1 (GH #412 comment check) is cheap and actionable: if 0 comments after 14 days,
escalate to owner directly. This is valuable independently. Phase 2 (backend API) requires a
service token, but `/api/appointments` or equivalent could be made auth-optional for a
`count` endpoint, or the nightly could use a read-only service key stored in GH Actions secrets.
However — this is implementation complexity that requires investigation, not just a SKILL.md edit.

### Round 3 (vs Idea 1)
**Challenge:** "Even if Step 9F is valid, is it HIGHER LEVERAGE than Idea 1? Idea 1 fixes the
root cause of why 40 issues are blocked, KB is 67 days stale, and referral reward can't be
verified. Step 9F monitors one product metric."

**Defend:** Step 9F is genuinely valuable but doesn't prevent systemic failures. Idea 1 addresses
the current 8-day blackout class. The booking tracker has lower structural impact than restoring
the full automated pipeline.

**VERDICT: WEAKENED** — Valid idea, condition re-enable met, but (a) mechanism complexity not
fully resolved, (b) lower structural leverage than Idea 1. Promoted to parking lot for run 91.
Condition: file as a nightly step once backend API mechanism is confirmed.

---

## Idea 3: Keys Koffee Business Hours Request GH Issue

### Round 1
**Challenge:** "GH #412 diagnostic SQL would tell us if Keys Koffee has booking_enabled=true
AND if they have availability rows. Filing a business hours issue before knowing booking state
is premature — might be asking for the wrong thing."

**Defend:** PR #404 code review explicitly wrote: 'Keys Koffee still needs real hours from
tenant.' This is author-level evidence at the time of writing the booking defaults code. The
author knew Keys Koffee's state. Additionally, even if booking_enabled=false, the sequential
next step would be: enable booking, THEN add hours. Filing the hours issue now doesn't hurt —
it just queues ahead of the dependency.

### Round 2
**Challenge:** "This is the 5th sequential GH issue targeting the booking funnel. The owner
isn't acting on existing issues (#399, #403, #412, #413). Another GH issue enters a queue
that's already backed up."

**Defend:** Different actor. #399/#403 require Railway/GitHub admin action. #412 requires SQL
execution. #413 requires UX review. The Keys Koffee issue requires a tenant email — a 60-second
action the owner can do on their phone. It's the lowest-friction item in the queue. But the
objection is valid: queue fatigue is real.

### Round 3 (vs Idea 1)
**Challenge:** "Is Keys Koffee the highest-leverage item when GH #403 + #399 fix would
unlock 40 ai-ready issues, restore KB, enable referral loop verification — all at once?"

**Defend:** No, it isn't. Keys Koffee adds one booking tenant. Idea 1 unlocks the full
autonomous pipeline. Structural impact is an order of magnitude different.

**VERDICT: WEAKENED** — Valid bonus action, not winner material. Execute as Bonus Action
alongside winner (file Keys Koffee hours request GH issue while committing run artifacts).

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 1: GH Actions Secrets Health-Check | SURVIVES | **WINNER** |
| Idea 2: Step 9F Booking Tracker | WEAKENED | Parking lot → run 91 |
| Idea 3: Keys Koffee Hours GH Issue | WEAKENED | Bonus Action this run |
| Idea 4: Supabase MCP Headless Diagnosis | Not debated | Parking lot |
| Idea 5: Weekly Revenue Digest | Not debated | Parking lot |
