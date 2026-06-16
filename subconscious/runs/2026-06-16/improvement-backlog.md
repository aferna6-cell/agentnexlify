# Improvement Backlog — 2026-06-16

## Active
- Wire check_project_invariants.py into pre-commit as Check 13 (6-line bash, AUTONOMOUS-EXECUTABLE, run 58 winner)

## Parking Lot (survived debate but not chosen)
- **RequirePaid.jsx smoke E2E** — write e2e/pay-gate.spec.ts: login as exempt tenant, verify dashboard loads. 30 min, S-effort. Deferred: moratorium active, not blocking. Escalate if pay gate regression reported.
- **AI-to-Human Handoff v1** — 61 days Critical, os_outbound_mirror.py reduces scope to ~1 day. Oldest pending customer value item. First post-moratorium candidate.
- **email_sequences.py god-class split** — 1143L (down from 1255L), still over 600L. Prerequisite: moratorium exits + GH #181 moot confirmed.
- **JWT stale plan claims (M3)** — deferred per launch audit. Practical risk likely limited to UI display drift; ai_usage_guard.py may read DB directly. Revisit if billing support tickets surface wrong-plan errors.
- **Cross-tenant isolation test for os_graph_memory** — parking lot from run 54. No new evidence.
- **Add tenant scope checklist to schema-discipline.md** — parking lot from run 54. Promote when next Agent OS service ships.
- **Fix kb-autopopulate.sh** — agent-browser CLI not installed. KB stale 35+ days. S-effort: replace agent-browser with curl/WebFetch or add silent-fail fallback.

## Rejected This Run
- **Fix JWT stale plan claims (M3)** — KILLED. Deliberately deferred by launch audit engineers. Correct judgment: M-L effort, hot-path risk, not moratorium-friendly. Do not re-propose as subconscious winner until post-moratorium and specific billing support tickets confirm the risk is real.

## Governance Corrections Applied This Run
- **Run 55** → implemented (3234597)
- **Run 57** → implemented (3234597)
- **Run 56** → superseded (Check 2 already covers from __future__)
- **Runs 30/31/32/34/51** → superseded_moot (9bed342 billing repricing made GH #181 and PR #183 moot)
- **runs_implemented** updated 16 → 18

## Questions for Next Run
1. Was Check 13 wired by nightly review? (`grep -c "Check 13" scripts/hooks/pre-commit`)
2. Did the repricing (9bed342) introduce any new billing test gaps? (`test_two_plan_repricing.py` covers 440 lines — is AMOUNT_TO_PLAN {1999/9999} now guarded by Check 11, or does Check 11 need updating?)
3. Is the moratorium exit condition met after governance corrections? (pending_approvals after corrections: ~6 — still above threshold of 2)
4. Has RequirePaid.jsx pay gate been exercised by real signups? Any false-lock reports?
5. Is kb-autopopulate.sh still broken, or was agent-browser installed?
