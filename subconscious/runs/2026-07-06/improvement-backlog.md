# Improvement Backlog — Run 80 (2026-07-06)

Items carried forward from prior runs + new parking lot additions from this run.

---

## Active Parking Lot

### P-SMS: SMS Compliance Dashboard → GH issue for issue-to-pr-loop
**Source:** Runs 70, 73, 74, 75, 76. Parking lot this run (debate-log.md Idea 2).
**Status:** pending_autonomous (GH issue with `ai-ready` label — issue-to-pr-loop channel)
**Evidence:** 12/12 council score (run 70). backend/routers/sms_compliance.py MISSING. frontend/src/pages/SmsCompliance.jsx MISSING. Run 74 paste-ready code blocks available. Run 76 mandate (file GH issue) satisfied by nightly 2026-07-01. Issue-to-pr-loop is the correct execution channel.
**Next run trigger:** Run 81 (if Step 9C mandate resolved) — verify GH issue exists and is ai-ready labeled.
**Effort:** S (2-4h implementation, 0 min subconscious)

### P-BRAIN-EVIDENCE: Add brain/INGESTION-LOG.md to subconscious Phase 2 evidence sources
**Source:** Run 80 Idea 3 (debate-log.md). WEAKENED by Step 9C priority but valid.
**Status:** parking lot
**Evidence:** Runs 77 and 78 ideated without knowing brain was stale. Adding INGESTION-LOG.md check to Phase 2 gathering improves ideation quality.
**Next run trigger:** Run 81 (after Step 9C mandate resolved — no competing mandate).
**Effort:** XS (3 lines in subconscious SKILL.md Phase 2 evidence commands block)

### P-001: Plan-Name Guard Check 7
**Source:** Runs 72, 73, 74, 75, 76, 77, 78, 79 parking lot.
**Status:** parking lot (XS effort, no urgency)
**Evidence:** No new plan-name violations detected. Pre-commit doesn't enforce plan naming conventions. Low priority until next plan naming incident.
**Effort:** XS

### P-004: Diagnose /healthz handler root cause
**Source:** Run 77 parking lot.
**Status:** parking lot (single data point, insufficient for root cause)
**Evidence:** /healthz timed out 2026-07-02 10:27 UTC. Only one incident. GH #393 P0 escalated. healthz-alert.sh still missing (run 77 → 78 → 79 chain). Re-evaluate after second incident.
**Effort:** S

### P-EMAIL: email_sequences.py god-class split
**Source:** Runs 41+, parking lot repeatedly.
**Status:** parking lot (M effort, moratorium active, no imminent edit)
**Evidence:** email_sequences.py is a god class (1143+ lines at run 70). No planned edits. Moratorium blocks M-effort items until pending ≤ 2.
**Effort:** M

---

## Rejected This Run

| Idea | Verdict | Reason |
|------|---------|--------|
| check_project_invariants.py brain freshness invariant (Idea 5) | REJECTED | Wrong layer — commit-time invariant is not the right mechanism for operational health monitoring |

---

## Mandate Chain Status

| Mandate | Source | Status |
|---------|--------|--------|
| Add Step 9C to nightly SKILL.md | Run 80 (fires unconditionally) | EXECUTING — Step 9C in winning-concept.md, pending nightly commit |
| Fix brain connector credentials | Run 79 winner, GH #394 | PENDING HUMAN — credentials still expired Jul 6 |
| ops/monitoring/healthz-alert.sh | Run 77 winner, P0 GH #393 | ESCALATED — P0 GH issue filed run 79, human action required |
| SLACK_ALERT_WEBHOOK_URL | Run 78/79 human step | DOCUMENTED in ops/monitoring/SETUP.md (or pending write) — no further automated mandate |

---

## Notes

- Brain connectors failing 6 consecutive days as of run 80. GH #394 is the credential fix ticket (human action). Step 9C ensures future expirations are caught in ≤24h.
- Moratorium: still active. max_pending_approvals=2. Step 9C is AUTONOMOUS-EXECUTABLE (no queue impact). SMS Dashboard GH issue goes to issue-to-pr-loop (different channel, no queue impact).
- Run 81 forecast: if Step 9C adds cleanly → SMS Compliance Dashboard GH issue verification as primary. If brain connector still failing → mandate governs (run 81 §mandate field in this run's winning-concept.md).
