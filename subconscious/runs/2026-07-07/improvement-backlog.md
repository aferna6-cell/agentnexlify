# Improvement Backlog — Run 81 (2026-07-07)

Items carried forward from prior runs + new parking lot additions from this run.

---

## Active Parking Lot

### P-KB-CRON: Diagnose KB Autopopulate Cloud Cron Root Cause
**Source:** Run 81 Idea 2 (debate-2.md). NEW — not in prior backlog.
**Status:** parking lot
**Evidence:** `knowledge-base/log.md` last entry 2026-05-05 (63+ days). Fix 65284cc shipped 2026-06-30 but cron unconfirmed in cloud container. Morning digest 2026-07-01 + nightly 2026-07-07 both confirm DEGRADED. All agents on stale knowledge.
**Next run trigger:** Run 82 PRIMARY CANDIDATE. Mandate: read `scripts/daily/kb-autopopulate.sh` + check Railway/GH Actions config → identify root cause → autonomous fix if code/config, else GH issue with exact steps.
**Effort:** S (diagnosis XS, fix XS-to-human-required depending on root cause)

### P-SMS: SMS Compliance Dashboard → GH #385 with `ai-ready` label (pending execution)
**Source:** Runs 70, 73, 74, 75, 76, 80. Run 81 WINNER activated.
**Status:** pending_autonomous (ai-ready label being added this run → issue-to-pr-loop channel)
**Evidence:** 12/12 council score (run 70). backend/routers/sms_compliance.py MISSING. frontend/src/pages/SmsCompliance.jsx MISSING. Run 74 paste-ready code blocks available. GH #385 OPEN (2026-07-01). ai-ready label ADDED this run.
**Next run trigger:** Run 82 — verify PR exists from issue-to-pr-loop. If no PR: diagnose loop failure.
**Effort:** S (2-4h implementation, 0 min subconscious after label add)

### P-BRAIN-EVIDENCE: Add brain/INGESTION-LOG.md to subconscious Phase 2 evidence sources
**Source:** Run 80 Idea 3 (debate-log.md). Run 81 Idea 3 (debate-3.md) — KILLED this run (timing: brain broken, deferred value).
**Status:** parking lot
**Evidence:** Runs 77 and 78 ideated without knowing brain was stale. Adding INGESTION-LOG.md check to Phase 2 gathering improves ideation quality.
**Next run trigger:** Run 82 SECONDARY — after GH #394 resolved (brain healthy → immediate value realized).
**Effort:** XS (3 lines in subconscious SKILL.md Phase 2 evidence commands block)

### P-001: Plan-Name Guard Check 7
**Source:** Runs 72, 73, 74, 75, 76, 77, 78, 79, 80, 81 parking lot.
**Status:** parking lot (XS effort, no urgency)
**Evidence:** No new plan-name violations detected. Pre-commit doesn't enforce plan naming conventions. Low priority until next plan naming incident.
**Effort:** XS

### P-004: Diagnose /healthz handler root cause
**Source:** Run 77 parking lot.
**Status:** parking lot (single data point, insufficient for root cause)
**Evidence:** /healthz timed out 2026-07-02 10:27 UTC. Only one incident. GH #393 P0 escalated. healthz-alert.sh NOW WRITTEN (nightly 460ea68). Re-evaluate after second incident.
**Effort:** S

### P-EMAIL: email_sequences.py god-class split
**Source:** Runs 41+, parking lot repeatedly.
**Status:** parking lot (M effort — **MORATORIUM NOW LIFTED** — eligible but no scheduled work)
**Evidence:** email_sequences.py is a god class (1143+ lines at run 70). No planned edits. Moratorium LIFTED this run (pending=1 ≤ max=2). M-effort now eligible but no human capacity identified.
**Effort:** M

---

## Rejected This Run

| Idea | Verdict | Reason |
|------|---------|--------|
| KB autopopulate diagnosis (Idea 2) | KILLED → parking lot run 82 | S effort, uncertain scope, outcompeted by XS certain Idea 1 |
| INGESTION-LOG.md in Phase 2 (Idea 3) | KILLED → parking lot | Deferred value while brain broken; step 9C covers escalation path |
| Plan-Name Guard Check 7 (Idea 4) | Not debated | XS but no urgency; parking lot carry-forward |
| email_sequences.py split (Idea 5) | Not debated | M effort, moratorium lifted but no capacity |

---

## Mandate Chain Status

| Mandate | Source | Status |
|---------|--------|--------|
| Add `ai-ready` label to GH #385 | Run 81 (fires — mandate from run 80 found gap) | EXECUTING — label add this run, issue-to-pr-loop activates |
| Verify issue-to-pr-loop picks up #385 | Run 81 → run 82 mandate | PENDING — check run 82 |
| Fix brain connector credentials | Run 79 winner, GH #394 | PENDING HUMAN — credentials still expired Day 7 |
| ops/monitoring/healthz-alert.sh | Run 77 winner, P0 GH #393 | IMPLEMENTED — nightly 460ea68 (2026-07-07) |
| SLACK_ALERT_WEBHOOK_URL | Run 78/79 human step | PENDING HUMAN — GH #391 open |
| KB autopopulate diagnosis | Run 81 new item → run 82 | PARKING LOT — run 82 primary |

---

## Notes

- Brain connectors failing 7 consecutive days as of run 81. GH #394 open. Step 9C now active (detects ≥3 consecutive failures, deduplicates GH issue).
- Moratorium LIFTED this run: pending_human = 1 (run 79 only), max = 2. M-effort items now eligible.
- SMS Dashboard: ai-ready label added this run → issue-to-pr-loop now active on #385. Run 82 verifies PR exists.
- KB autopopulate: 63 days degraded. Run 82 primary mandate: diagnose root cause.
- P-EMAIL: moratorium lifted — eligible for run 82+ once SMS Dashboard delivered.

- Run 82 forecast: (1) verify SMS Dashboard PR from issue-to-pr-loop, (2) diagnose KB autopopulate cron, (3) INGESTION-LOG.md in Phase 2 after GH #394 resolved.
