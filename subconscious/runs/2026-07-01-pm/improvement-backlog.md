# Improvement Backlog — Run 2026-07-01-pm (Run 76)

Generated: 2026-07-01 (PM run)

---

## Active (Pending Human Approval or Autonomous Execution)

| ID | Item | Type | Effort | Run Added | Status |
|----|------|------|--------|-----------|--------|
| B-001 | Zapier plan_status enforcement (de-scoped) | AUTONOMOUS-EXECUTABLE | XS | Run 75 (mandate fires Run 76) | pending_autonomous |
| B-002 | SMS Compliance Dashboard frontend (SmsCompliance.jsx + router) | HUMAN-REQUIRED | S | Run 73 | pending — GH issue filed nightly 2026-07-01, issue-to-pr-loop active |
| B-003 | email_sequences.py god-class split | HUMAN-REQUIRED | M | Run 41 | parking lot — moratorium, no trigger |
| B-004 | Plan-name guard pre-commit hook | AUTONOMOUS-EXECUTABLE | XS | Run 76 | parking lot — no urgency |

---

## Frozen (Not Subconscious Cycle Material)

| ID | Item | Reason | Frozen Run |
|----|------|--------|-----------|
| F-001 | Widget drift fix (landing-page-v2) | 6 delivery failures, human-only filesystem fix. RETIRED at Run 70. | Run 70 |
| F-002 (candidate) | AI-to-Human Handoff | 7 consecutive kills in debate. Requires dedicated sprint. | Pending freeze at Run 77 if still unimplemented |

---

## Completed (Historical)

| Item | Completion | Run |
|------|-----------|-----|
| KB autopopulate WebFetch fix | Commit 65284cc (2026-06-30) | Runs 71-72 |
| KB autopopulate DISCOVER_PROMPT fix | Commit 65284cc (2026-06-30) | Run 71 |
| SMS Compliance backend (sms_compliance.py + migration 160) | Confirmed shipped | Run 73 |

---

## Moratorium Status

Active: true  
True pending (human-required): ~2 (SMS Dashboard + email split)  
True pending (autonomous): ~1 (Zapier fix)  
Max before moratorium blocks: 2 (per governance.json)  

Moratorium applies to: new HUMAN-REQUIRED items  
Moratorium does NOT apply to: AUTONOMOUS-EXECUTABLE with security/revenue override (Zapier fix bypasses)

---

## Notes

- B-001 (Zapier): De-scoped per run 76 mandate. Test file deferred. If not implemented by run 77, escalate to CRITICAL + file GH issue directly.
- B-002 (SMS Dashboard): nightly-commit-review path activated. Do not re-recommend in subconscious until GH issue closes or stalls.
- F-002 (AI-to-Human Handoff): 7 consecutive debate kills. Recommend freezing in governance.json after run 77.
