# Run 105 — Candidate Ideas (2026-07-27)

**Evidence window:** 2026-07-24 – 2026-07-27 (repo idle 4 days)
**Run mandate from run 104:**
1. Step 9H fired? → NOT YET (PR #577 not merged → Step 9H not on main)
2. GH #500 daily ping added? → NOT YET (same root cause)
3. GH #500 resolved? → OPEN (7+ days, no evidence of fix)
4. PR #577 merged? → NO (open/draft since 2026-07-24)
5. Managed Agents Phase 0 GH issue approved? → UNKNOWN (run 103 winner, pending_approval=true)
6. GH #399 rotated? → OPEN (AUTOPILOT_GH_TOKEN still expired)

---

## Idea 1 — PR #577 merge-readiness comment
**Category:** operational
**Effort:** XS
**Confidence:** HIGH
**Autonomous-executable:** YES (GH comment)
**Requires human:** NO (comment only; human still merges)

Subconscious run 102 implemented Step 9G; run 104 implemented Step 9H. Both are on branch `subconscious/run-101-step-9g`, verified (9G: 7 occurrences, 9H: 5 occurrences). PR #577 has been open as draft for 3 days with no merge. CI is red due to GH #500 (spending limit), not this PR's content. The human may not realize the PR is merge-ready despite red CI.

**Action:** Post a comment on PR #577 with: local verification commands, explanation that CI failure is GH #500 (not this PR), list of what merging accomplishes (Steps 9G+9H active on nightly), confirmation of no code changes in PR.

**Evidence:** PR #577 open since 2026-07-24. Step 9G/9H implemented on branch (verified grep). KB currently fresh (4 days), Step 9G won't fire immediately. Step 9H would fire every nightly once on main. 

---

## Idea 2 — GH #500 Day-7 heartbeat comment
**Category:** operational
**Effort:** XS
**Confidence:** HIGH
**Autonomous-executable:** YES (GH comment)
**Requires human:** NO (comment only; human fixes billing)

GH #500 (Actions spending limit) has been open 7 days. Run 101 posted the initial comprehensive checklist comment on 2026-07-25. Step 9H is designed to add daily dated pings, but it won't fire until PR #577 merges. Adding a manual Day-7 heartbeat maintains urgency pressure while 9H waits for merge approval. This is exactly what Step 9H would do if it were active.

**Action:** Post comment on GH #500: "Day 7 manual heartbeat (subconscious run 105). Actions down since 2026-07-20. 30 ai-ready issues stalled. Fix: raise spending limit at github.com/settings/billing/summary. Step 9H ships with PR #577."

---

## Idea 3 — Managed Agents Phase 0 kickoff GH issue
**Category:** customer_value
**Effort:** XS
**Confidence:** MEDIUM
**Autonomous-executable:** YES (GH issue creation)
**Requires human:** YES (run 103 marked pending_approval)

Run 103 selected "Managed Agents Phase 0 kickoff GH issue" as winner but marked it pending_approval. The issue itself would just be a structured recommendation (set Railway env vars, MANAGED_AGENTS_ENVIRONMENT_ID, smoke test). No code changes. Managed agents registry is wired; Phase 0 is blocked only on env var provisioning. However, run 103 explicitly flagged this as requiring human approval before filing.

**Blocker:** run 103 pending_approval flag. Filing autonomously would override the approval gate.

---

## Idea 4 — email_sequences regression test gap GH issue
**Category:** code_health
**Effort:** XS
**Confidence:** MEDIUM
**Autonomous-executable:** YES (GH issue creation)
**Requires human:** NO

Commit ab1a7c2 (2026-07-23) split email_sequences.py (1143L) into 3 new files: email_crud.py (529L), email_enrollment.py (328L), email_processor.py (341L) + migration 187 (pending_automations RLS). No subconscious audit has checked test coverage on these new modules. With CI dark (GH #500), any test gap is invisible. Filing a GH issue now creates a debt record for when CI returns.

**Scope:** grep for test_email_ files, compare against new module surface area, file GH issue with ai-ready label when GH #399 resolved.

---

## Idea 5 — PR #575 merge: add reviewer comment on migration 188 note
**Category:** customer_value
**Effort:** XS
**Confidence:** MEDIUM
**Autonomous-executable:** YES (GH comment)
**Requires human:** YES (human still merges)

PR #575 (Fable 5 tenant-silence alert + Managed Agents Phase 0 prep) has been open as draft since 2026-07-23. It carries migration 188 as a file-only addition (intentionally not applied — awaits Phase 0 start). Adding a targeted review note clarifying "migration 188 is file-only, do not apply until Phase 0 start, all other changes are safe" directly addresses the main question a reviewer would have. 38 tests pass locally per PR body.

**Risk:** could read as pressure to merge; keep it factual.
