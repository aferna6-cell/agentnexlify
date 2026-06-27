# Idea 05: SMS Compliance Dashboard (TCPA Visibility)

**Category:** customer_value / operational
**Effort:** S-M (3-4 hours — piggybacks on council Fix #1 TCPA work)
**ROI:** 2.1 (liability visibility, differentiator for regulated industries)
**Age:** Bonus B from run 68/69, bonus from council sprint TCPA work
**Autonomous:** No — frontend component requires human review

## Evidence

- Council Fix #1 (commit 9ddfd0e): SMS opt-out suppression + TCPA compliance wired in
- `backend/services/os_outbound_mirror.py` (152 tests) handles opt-out suppression
- Customer gaps: SMS compliance visibility not surfaced to dashboard operators
- TCPA non-compliance risk: undocumented opt-outs, suppressed numbers not visible
- Council sprint shipped TCPA logic in backend — no dashboard surface for operators yet

## What

New dashboard section or badge in Settings/SMS page showing:
1. Count of opted-out numbers (suppressed from outbound SMS)
2. Last opt-out received timestamp
3. Total SMS sent this month vs. suppressed
4. Link to TCPA compliance guide (KB article or external link)

Source of truth: existing `sms_opt_outs` table (or equivalent opt-out tracking from `os_outbound_mirror.py`).

Backend: `GET /api/sms/compliance-stats` (2 queries: opt-out count, sent count from `sms_log` or `automation_events`).
Frontend: `SMSComplianceCard.jsx` component in Settings page.

## Risk

- Must verify opt-out table name (could be `sms_opt_outs`, `opt_out_list`, or embedded in `os_outbound_mirror.py` logic)
- Schema guardian review required for query construction
- Widget/SMS compliance visibility doesn't block any critical path — nice-to-have
- S-M effort overlaps with run 70 winner (AI-to-Human Handoff v1 also M effort) — can't do two M-effort items simultaneously

## Debate Position

**GOOD candidate** but lower priority than AI-to-Human Handoff (72-day gap, Critical all industries vs S-M effort, operational visibility only).

**Verdict:** WEAKENED → Bonus B. Included in improvement-backlog.md as next-sprint candidate after run 70 winner implemented. Piggybacks on council TCPA work when human is already in SMS codebase.
