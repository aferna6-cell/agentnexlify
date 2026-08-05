# Improvement Backlog — 2026-08-05 (Run 103)

## Active (winner this run)
- **KB Notes End-to-End Widget Retrieval Test** — Add `backend/tests/test_tenant_kb_widget_retrieval.py`. Insert note via API → KB search → assert in retrieval results → assert in widget context assembly. S-effort. HIGH confidence. Fresh evidence from 4853c31 (2026-08-02).

## Governance Mandate (human action required)
- **Step 9G PR merge** — PRs #625 and #626 both implement Step 9G (kb-autopopulate self-trigger). Main has 0 grep hits. KB 23 days stale. Human must merge one and close the other. Morning digest 2026-08-04 already flagged as top priority #1. Subconscious has recommended 7 consecutive runs (97-103). No further subconscious recommendation can break the logjam — human action only.

## Parking Lot
- **Step 9F silent-failure diagnostic** — KB 23 days stale but no Step 9F output in Aug 1-5 nightly logs. Possible path/format mismatch in SKILL.md bash block. Needs: GH #403 comment history to confirm or deny. If Step 9F is broken, Step 9G (when merged) would also not fire. File as GH issue once human confirms Step 9G PR status.
- **Expand client_id guard to all tables** — bug-patterns.md 2026-08-01: connector_awareness.py used `.eq("tenant_id", client_id)` on `tenant_api_keys`. Fix applied. But `widget_configs`, `appointments`, `analytics_events`, `tenant_plan` — column names unverified. Grep all `.eq("tenant_id", ...)` call sites. Effort M. Carry to run 102 if winner slot available.
- **Cross-phase integration test audit** — No tests cross widget→backend→KB→AI boundary end-to-end. KB notes gap (this run's winner) is one instance. Discovery task: grep backend/tests/ for cross-boundary test patterns, count gaps, rank. File GH issue with list. Not this run — winner slot taken.
- **AUTOPILOT_GH_TOKEN expired** — GH #399 open. Issue-to-PR loop blocked. Dependency on tenant rotating secret. Not actionable by subconscious.
- **Agent OS tenant count watch** — LoopHealthPage parking lot condition: if agent_os tenants ≥ 5, add health loop. Currently 2-3. No change.

## Retired / Resolved
- widget_drift_topic: retired (governance.json widget_drift_topic_retired=true)
- ai_human_handoff: frozen (too broad, not actionable in isolation)
- booking_cta_linkify_bug: resolved 2026-07-23

## Questions for Human
1. Has #625 or #626 been reviewed? What's blocking merge?
2. Is `backend/services/knowledge_base.py` (or equivalent) the right file for KB search — or is search in a different module?
3. Should KB notes e2e test be filed as a GH issue (for the issue-to-PR loop) or implemented directly in the next session?
