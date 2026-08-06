# Improvement Backlog — 2026-08-06 (Run 101)

## Winner (this run)
**Step 9G: KB Autopopulate Self-Healing Trigger** — 4th-cycle escalation, direct implementation authorized. Verbatim block in winning-concept.md.

---

## Parking Lot

### PR Dedup Guard Fix (Idea 2)
- **Problem:** Subconscious SKILL.md Phase 8 guard added at run 99 fails to prevent duplicate PRs. 7 subconscious draft PRs accumulate in repo (#625, #626, #613, #611, #606, #604, +more)
- **Root cause:** Undiagnosed. Likely: branch-name check passes but PR title check missing
- **Proposed fix:** Strengthen guard to check PR titles containing "subconscious:" in addition to branch name prefix. Cap: if >3 open subconscious PRs, halt branch creation + file dedup-required GH issue
- **Effort:** S
- **Confidence:** MEDIUM (root cause unconfirmed)
- **Executable:** yes (SKILL.md edit)
- **Why deferred:** Root cause undiagnosed. Better to diagnose before fixing. Idea 1 is more immediately load-bearing

### Tenant Conversation Heartbeat (Idea 3)
- **Problem:** No automated detection if a live tenant goes dark (widget broken, domain changed). Bug-patterns.md documents "widget missing 5 weeks, no automated detection"
- **Blocking constraint:** Supabase MCP unavailable in headless nightly sessions (confirmed runs 88, 89). Needs alternative mechanism (backend health endpoint or GH Actions context)
- **Effort:** M (blocked → actual effort XL until mechanism resolved)
- **Confidence:** MEDIUM
- **When to revisit:** After a backend health endpoint is designed that nightly can call without Supabase MCP

### Governance State Sync (Idea 5)
- **Problem:** governance.json active_directions has 15+ entries from runs 89-93, many stale (referral activation, Keys Koffee booking) — may be resolved or abandoned
- **Action:** Archive items >30 days with `status: superseded` into `archived_directions`
- **Effort:** M (requires human judgment on each item)
- **Executable:** Only with human review
- **When to revisit:** When PR debt is cleared and governance.json becomes hard to read

---

## Killed (this run)

- **Tenant conversation heartbeat (Idea 3):** Supabase headless gap makes it infeasible in the autonomous SKILL.md channel at current scale (3 tenants)
- **Step 9H MCP monitoring:** Killed at run 100 — 1 tenant only, premature observability. Status: rejected_paths in governance.json

---

## Ongoing Mandate Items (from governance)

1. **Step 9G in SKILL.md** — this run's winner (4th carry-forward, direct implementation)
2. **KB freshness** — has kb-autopopulate.yml run successfully since 2026-07-23? Check knowledge-base/log.md
3. **PR #625 / #626** — after Step 9G merged via this run's direct implementation, close one of these draft PRs as superseded
4. **GH #403** — Step 9F comments should now show Step 9G diagnostic output once implemented
5. **LoopHealthPage.jsx** — promote to implementation when Agent OS active tenants >5 (currently 2-3)
6. **MCP Step 9H** — revisit when MCP tenant count >5 (currently 1)
