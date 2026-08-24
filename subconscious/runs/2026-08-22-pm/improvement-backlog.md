# Improvement Backlog — Run 2026-08-22-pm (#109)

## Active (implementing this run)

| # | Title | Category | Status | Source |
|---|-------|----------|--------|--------|
| Step 9J | Dependabot Auto-Merge in nightly SKILL.md | operational | **IMPLEMENTING** | run 108 mandate → run 109 |

---

## Parking Lot (next candidates)

| # | Title | Category | Priority | Notes |
|---|-------|----------|----------|-------|
| Step 9K | Stale Subconscious PR Auto-Closer in nightly SKILL.md | workflow | run 110 candidate | Implement if >3 stale subconscious PRs confirmed open. PR dedup guard already prevents new duplicates. |
| Middleware fix | Add block_demo_role implementation sketch as comment on GH #669 | security | low-effort comment | NOT a new issue — GH #669 already tracks the problem. Sketch: add block_demo_role as default FastAPI dependency with auth/webhook/admin exclusions. |

---

## Carried Blockers (human-action required)

| Issue | Description | Age |
|-------|-------------|-----|
| GH #399 | AUTOPILOT_GH_TOKEN expired — 30 ai-ready issues stalled, issue-to-pr-loop dark | Day 41+ |
| GH #403 | ANTHROPIC_API_KEY (+ SUPABASE_URL/ANON_KEY) missing in GH Actions — KB embeddings skipped | 29d stale |
| GH #669 | 97/97 routers missing Depends(block_demo_role) — demo tenants can mutate data | Filed 2026-08-20, no PR yet |

---

## Frozen (do not propose)

| Title | Reason |
|-------|--------|
| ai_human_handoff | Governance: frozen. customer-gaps.md: Critical but out of scope for autonomous work. |

---

## Implemented (historical — this cycle)

| Step | Title | Run | Date |
|------|-------|-----|------|
| 9C | Brain connector health check in nightly | run 99 | 2026-07-20 |
| 9E | Proactive credential rotation tracking in nightly | run 100 | 2026-07-22 |
| 9F | KB autopopulate staleness check in nightly | run 101 | 2026-07-23 |
| 9G | KB autopopulate self-healing trigger in nightly | run 103 | 2026-08-10 |
| 9I | Demo-role security sweep in nightly | run 107 | 2026-08-19 |
| **9J** | **Dependabot auto-merge in nightly** | **run 109** | **2026-08-22** |
