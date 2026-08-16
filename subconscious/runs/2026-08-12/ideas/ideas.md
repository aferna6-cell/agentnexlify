# Run 103 — Ideas (2026-08-12)

## Evidence Inputs (Phase 2 summary)
- **git log 7d**: 3 commits (f315f6f subconscious run 102, 611d58e morning-digest-2026-08-11, 926d798 nightly-commit-review-2026-08-11)
- **nightly log**: 2026-08-12 — all 9 steps ran; 0 auto-fixes; detached HEAD guard fired + fixed; Step 9D stalled (5/5 autopilot failures); Step 9G triggered kb-autopopulate.yml (204 queued)
- **skill-discovery-2026-08-10**: Proposed route-security-guard-audit + pr-backlog-triage; rejected KB staleness trigger (already in SKILL.md) and competitor teardown pipeline
- **bug-patterns.md**: connector_awareness.py `tenant_id` instead of `client_id`; booking CTA plain text (0 real bookings weeks); silent-green automation
- **customer-gaps.md**: AI-to-human handoff (Critical, frozen), Lead source analytics (pending_autonomous), Custom automation templates (Medium)
- **knowledge-base/log.md**: 8 new articles compiled 2026-08-12 — KB 114→124 articles, Step 9G triggered compile succeeded
- **GH issues**: #643 open 5d (appointment_briefs.py missing block_demo_role + plan gate + ai_usage_guard, security+ai-ready), #399 open (AUTOPILOT_GH_TOKEN expired, 39d), #403 open (SUPABASE_ACCESS_TOKEN unknown)
- **run_103_mandate check**: response_score.py N/A (file doesn't exist); KB freshness RESOLVED (114→124 articles); detached HEAD guard CONFIRMED in SKILL.md; route-security-guard-audit still pending_approval; GH #643 still open

---

## Idea 1: route-security-guard-audit SKILL.md (carry-forward run 102)
**Category:** code_health
**Effort:** S
**Confidence:** HIGH

Create `.claude/skills/route-security-guard-audit/SKILL.md` with a 6-step auditing checklist for the `block_demo_role` FastAPI dependency guard.

**Evidence:**
- `cbbaae5` (2026-08-07): nightly applied fix on detached HEAD — commits orphaned, never merged
- `c204af2` (2026-08-08): same fix re-applied correctly after orphaned-commit discovery
- `228203d` (2026-08-08): structural test added to prevent silent regression
- GH #643 (open 5d): appointment_briefs.py still missing `block_demo_role` + plan gate + `ai_usage_guard` — security+ai-ready, stalled while autopilot loop dead
- skill-discovery-2026-08-10: independent explicit proposal of this exact SKILL.md with same 6-step structure
- Same 15-min re-discovery cost (billing.py:33 reference, test introspection pattern) paid twice in 48h

**Action:** Write `.claude/skills/route-security-guard-audit/SKILL.md` — documentation-only change, 6-step process covering: grep guard inventory, identify missing routes, add `Depends(block_demo_role)`, add `ai_usage_guard` for AI-adjacent routes, add structural test in `test_plan_gating_new_plans.py`, syntax check + commit pattern.

**Status:** RECOMMENDED — awaiting human approval (1-run carry-forward, not a loop)

---

## Idea 2: pr-backlog-triage SKILL.md
**Category:** workflow_efficiency
**Effort:** S
**Confidence:** MEDIUM

Create `.claude/skills/pr-backlog-triage/SKILL.md` — skill to classify open PRs into merge-ready / superseded / stale-draft / active and apply appropriate actions.

**Evidence:**
- skill-discovery-2026-08-10: explicit proposal, 5-6 stale autonomy DRAFTs in morning digest multiple consecutive days
- Morning digest 2026-08-10: 10 open PRs, 6 stale autonomy DRAFTs flagged as top-3 priority
- Morning digest 2026-08-07: same pattern, 8 open PRs
- Current: 5 subconscious draft PRs open (#626 9d, #613 11d, #611 12d, #606 14d, #575 19d)

**Weakness:** PR pile-up root cause is owner decision (not skill gap) — there are no "obviously merge-ready" Dependabot PRs confirmed merged today. skill-discovery proposal is solid but the urgency is medium (no active PR conflicts). Run 102 already put this in parking lot correctly.

**Status:** WEAKENED → parking lot

---

## Idea 3: GH #399 Day-39 escalation comment
**Category:** operational
**Effort:** XS
**Confidence:** MEDIUM

Post a Day-39 escalation comment on GH #399 (AUTOPILOT_GH_TOKEN rotation) with quantified opportunity cost.

**Evidence:**
- GH #399 open 39 days as of 2026-08-12 (opened 2026-07-04)
- 5/5 autopilot runs failing per nightly-2026-08-12 Step 9D
- GH #643 would be picked up by autopilot loop within 24h of token rotation
- Step 9D already posted stall notice on #399 this run (bonus action done by nightly)

**Weakness:** Nightly Step 9D already commented on #399 today. Making this the subconscious WINNER is redundant — nightly handles ongoing comments. Winner slot should go to a systemic fix, not a comment that's already being automated.

**Status:** WEAKENED → parking lot (Step 9D handles ongoing escalation)

---

## Idea 4: feature-build SKILL.md — canonical 5-file pattern addition
**Category:** workflow_efficiency
**Effort:** XS
**Confidence:** MEDIUM

Add the canonical 5-file feature set to `.claude/skills/feature-build/SKILL.md`: router + service + tests + page + api-util.

**Evidence:**
- skill-discovery-2026-08-10: proposed as "Existing Skill Update" — not a new skill
- Two recent features (e0e9be6 + 4853c31) both follow exact same 5-file pattern
- Currently undocumented in feature-build SKILL.md

**Weakness:** "Existing Skill Update" per skill discovery (lower priority than new skill). No active bugs caused by this gap right now. Medium-confidence fix for a medium-impact documentation gap.

**Status:** PARKING LOT — lower priority than Idea 1

---

## Idea 5: Step 9H redesign — idempotent PR pile alerter
**Category:** operational
**Effort:** S
**Confidence:** LOW

Redesign Step 9H in nightly-commit-review SKILL.md to use idempotent alerting (track last-alerted PR count to avoid firing every run).

**Evidence:**
- run 101 parking lot candidate: "Step 9H redesign (idempotent PR pile alerter — current design would fire every nightly indefinitely)"
- 5 stale subconscious PRs accumulating (no change from run 102)

**Weakness:** KB freshness was just RESOLVED by Step 9G (114→124 articles compiled 2026-08-12) — the original Step 9H urgency was KB-related. PR pile-up is a different problem from what Step 9H was originally addressing. Low-confidence that redesigning Step 9H now is the right move when pr-backlog-triage (Idea 2) is a cleaner solution to the PR problem.

**Status:** KILLED — KB resolved by Step 9G; PR pile addressed better by pr-backlog-triage in parking lot

---

## Summary
| Idea | Status | Reason |
|------|--------|--------|
| 1. route-security-guard-audit SKILL.md | **WINNER** | Double-validated, active GH #643, 1-run carry (not loop) |
| 2. pr-backlog-triage SKILL.md | Parking lot | Valid but not urgent enough for winner slot; root cause is owner decision |
| 3. GH #399 Day-39 comment | Parking lot | Step 9D already handles ongoing comments automatically |
| 4. feature-build 5-file pattern | Parking lot | Existing skill update, no active bugs caused by gap |
| 5. Step 9H redesign | Killed | KB resolved by Step 9G; PR problem better addressed by pr-backlog-triage |
