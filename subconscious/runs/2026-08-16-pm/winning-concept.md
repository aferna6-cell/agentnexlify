# Run 105 — Winning Concept (2026-08-16-pm)

## Create route-security-guard-audit SKILL.md

**Category:** code_health  
**Effort:** S (~30 min to write + verify)  
**Confidence:** HIGH  
**Status:** AUTONOMOUS-EXECUTABLE — DIRECT IMPLEMENTATION (3rd carry-forward per run 99/Step 9F precedent)

---

## Problem

`block_demo_role` prevents demo tenants from mutating billing, payment, subscription, and AI-usage-critical endpoints. Without it, demo accounts can call any endpoint the guard is missing from.

Two confirmed gaps, two separate GH issues:
- `appointment_briefs.py` — GH #643 (8 days open, demo can create/delete appointment briefs)
- `scoring_config.py` — GH #661 (filed 2026-08-16, demo can create/update/delete scoring factors, reset to defaults)

130+ router files in `backend/routers/` — most unaudited. Pattern is recurring: new routers ship without the guard check.

**Prior fixes are one-off.** Each gap gets a separate GH issue, a separate PR, a separate review cycle. No systematic detection exists. The fix for issue N does not prevent issue N+1.

**This SKILL.md creates the systematic detection layer.** Every future audit uses the same 6-step checklist. Nightly review can invoke it on PR merges. Issue-to-PR loop can run it when a security label appears.

---

## Why This Wins (3rd Carry-Forward → Direct Escalation)

1. **Governance mandate.** run_105_mandate item 2: "route-security-guard-audit SKILL.md: 3rd carry-forward — ESCALATE to AUTONOMOUS-EXECUTABLE." No ambiguity.
2. **Precedent confirmed.** Run 99/Step 9F recommended for 3 cycles → run 101 implemented directly. Same path, same mechanism.
3. **Content ready.** Full 6-step audit specification written in run 102 winning concept (subconscious/runs/2026-08-11-pm/winning-concept.md). This is not a new design; it's a long-pending implementation.
4. **Evidence compounds.** Run 102: 1 confirmed gap (appointment_briefs). Run 103: carry-forward. Run 104: second gap found (scoring_config). Each run adds evidence; each run without the skill is a missed detection cycle.
5. **Zero blast radius.** New file in `.claude/skills/`. No code changes, no migrations, no dependencies. Fully reversible.

---

## Implementation

**File created:** `.claude/skills/route-security-guard-audit/SKILL.md`

### 6-step checklist (embedded in SKILL.md):
1. `grep -rn "block_demo_role" backend/routers/` — build guard inventory
2. Identify mutating endpoints missing the guard (POST/PUT/DELETE/PATCH without block_demo_role)
3. Add guard: `@router.post("/endpoint", dependencies=[Depends(block_demo_role)])`
4. Add structural test in `test_plan_gating_new_plans.py`
5. Syntax verify: `python -c "import ast; ast.parse(...)"`
6. Commit: `fix(security): add block_demo_role to <router> endpoints`

### Triggers:
- Any router file in `backend/routers/` touched in a PR with new mutating endpoints
- Nightly review flags missing security dependency
- GH issue labeled `security` + `ai-ready` references `block_demo_role`
- Manual: user says "audit security guards" or "check block_demo_role coverage"

---

## Bonus Action: Step 9J Recommended (not implemented this run)

Today's nightly found 7 commits orphaned in detached HEAD — caught manually only. Step 9J would add automated detection: `git log origin/main..HEAD --oneline | wc -l` → alert if > 0. Recommended for next nightly SKILL.md edit pass (XS effort, AUTONOMOUS-EXECUTABLE).

---

## Carry-Forward Note

- **appointment_briefs.py fix (GH #643):** PENDING-APPROVAL. Human must approve security code change. GH issue filed. Not in subconscious scope (requires human review gate).
- **scoring_config.py fix (GH #661):** PENDING-APPROVAL. Same class. GH issue filed 2026-08-16.

---

## Next Action

Subconscious run 105 APPLIES this directly: `.claude/skills/route-security-guard-audit/SKILL.md` created. Push to `subconscious/run-103` branch (PR #653). Run 106 mandate: verify skill is invocable, verify appointment_briefs.py + scoring_config.py status.
