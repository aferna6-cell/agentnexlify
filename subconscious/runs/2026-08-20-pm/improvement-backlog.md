# Improvement Backlog — Run 2026-08-20-pm (Run 109)

## Implemented This Run

| Item | Status | Notes |
|------|--------|-------|
| Step 9J (Dependabot auto-merge) | IMPLEMENTED | Mandate fires (1st carry-forward, run 109). Block inserted in nightly-commit-review/SKILL.md. |

---

## Parking Lot (carry to run 110)

| Item | Priority | Condition | Notes |
|------|----------|-----------|-------|
| Step 9K (stale subconscious PR commenter) | MEDIUM | ≥3 subconscious PRs open (MET: 5 open) | Comment-only version safe. Debate verdict: valid but weakened — defer since Step 9J is mandate winner. Run 110 candidate if PR count still ≥3. |
| GH #403 SUPABASE_URL diagnostic comment | LOW | KB still stale | Bonus action from run 108/109. Post if KB staleness persists at run 110. Lists all 3 required secrets (ANTHROPIC_API_KEY + SUPABASE_URL + SUPABASE_ANON_KEY). |
| GH #669 middleware sketch | LOW | GH #399 unblocked | Non-structural. Issue-to-pr-loop will handle when GH #399 resolved. |

---

## Blocked (human-gated, not solvable by subconscious)

| Item | Blocker | Age | Notes |
|------|---------|-----|-------|
| KB autopopulate (6 AM / 6 PM) | GH #403: ANTHROPIC_API_KEY missing from GH Actions | 28d stale | Run 107 posted comment. Run 108 proposed SUPABASE_URL diagnostic. No human action. |
| issue-to-pr-loop (30 ai-ready issues queued) | GH #399: AUTOPILOT_GH_TOKEN expired | Day 40+ | Blocks all autonomous issue execution. |
| block_demo_role on 97 routers (GH #669) | GH #399 blocks autopilot implementation | — | Middleware approach reduces 95-file problem to 1 file. Filed as GH #669. |

---

## Frozen Ideas (no further debate)

| Item | Reason |
|------|--------|
| ai_human_handoff | Governance freeze — not revisited until GH #399 resolved |

---

## Run 110 Mandate

1. Verify Step 9J executed: check nightly-2026-08-2X log for "Step 9J: {N} checked, {M} merged, {K} skipped"
2. Dependabot PRs: how many merged (#629/#630/#631/#649/#665/#666)?
3. Step 9K candidate: if subconscious PR count still ≥3, implement Step 9K (stale PR commenter, comment-only)
4. GH #403: has SUPABASE_URL diagnostic comment been acted on? KB freshness?
5. GH #399: resolved? (Day 40+)
6. GH #669: any human action on middleware recommendation?
