# Run 105 — Ideas (2026-08-16)

## Evidence Base
- Nightly 2026-08-16: 2 commits triaged (docs only), 0 code bugs
- SUPABASE_ACCESS_TOKEN Action Required section added by nightly (run 104 autonomous winner — EXECUTED)
- GH #661 filed by nightly: scoring_config.py missing block_demo_role on 4 mutating endpoints
- Structural finding: 6 commits in detached HEAD, not yet at origin/main
- KB staleness: 24 days (Step 9G triggers but ANTHROPIC_API_KEY missing blocks compile)
- route-security-guard-audit SKILL.md: MISSING — run 102 winner, 3rd carry-forward (mandate fires)
- GH #394 (brain connector): 23+ days open, SUPABASE_ACCESS_TOKEN unknown state
- GH #399 (AUTOPILOT_GH_TOKEN): 37+ days open, autopilot loop stalled
- GH #643 (appointment_briefs block_demo_role): PR #653 draft, needs human review
- GH #661 (scoring_config block_demo_role): filed today by nightly

---

## Idea 1 — Write route-security-guard-audit SKILL.md (3rd-cycle escalation)

**Category:** code_health  
**Effort:** XS (content fully specified in run 102 winning-concept.md)  
**Confidence:** MAXIMUM  
**Autonomous-executable:** YES — 3rd carry-forward triggers direct implementation per subconscious precedent

**Evidence:**
- Run 102 winner (2026-08-11-pm): PENDING APPROVAL
- Run 103: 1st carry-forward (MISSING)
- Run 104: 2nd carry-forward (MISSING)
- Run 105 mandate item 2: "3rd carry-forward — ESCALATE to AUTONOMOUS-EXECUTABLE"
- Precedent: Step 9F (run 97→99 3 cycles → direct implementation), Step 9G (run 100→101 direct escalation at 6 PR-channel cycles), Step 9C (run 103 same-day autonomous)
- GH #661 confirms 2nd instance of block_demo_role gap (scoring_config.py) — same class as #643

**Action:** Write `.claude/skills/route-security-guard-audit/SKILL.md` using content from subconscious/runs/2026-08-11-pm/winning-concept.md (verbatim). No human approval gate — mandate fires.

---

## Idea 2 — Add Step 9I: nightly grep scan for missing block_demo_role

**Category:** code_health  
**Effort:** S  
**Confidence:** HIGH  

**Evidence:** 2 confirmed instances (appointment_briefs.py + scoring_config.py) in 9 days. Systematic scan would detect the full set. GH #661 just filed — scan would catch any new gaps proactively.

**Weakener:** The route-security-guard-audit SKILL.md (Idea 1) is the structural fix. A nightly grep is lower-leverage than a skill that teaches how to audit AND fix. Do the skill first; the nightly scan is a downstream companion.

---

## Idea 3 — Add block_demo_role to scoring_config.py (GH #661)

**Category:** security  
**Effort:** S  
**Confidence:** HIGH  

**Evidence:** GH #661 filed today. 4 mutating endpoints at /api/v1/scoring missing block_demo_role. Demo tenants can manipulate scoring factors.

**Weakener:** Code fix = execution task requiring human review (security change). GH #661 already filed — that's sufficient subconscious output. Autopilot loop stalled (GH #399). Fix requires issue-to-pr-loop or human, not subconscious. Subconscious should not implement security code changes directly.

---

## Idea 4 — Comment on GH #394 with exact brain connector recovery checklist

**Category:** operational  
**Effort:** XS  
**Confidence:** MEDIUM  

**Evidence:** GH #394 open 23+ days. SUPABASE_ACCESS_TOKEN now in credential-rotation-schedule.md with Action Required note. Human needs specific steps to recover brain connector.

**Weakener:** Credential rotation requires human judgment (dashboard access, actual token values). GH comment would be a 4th autonomous comment on the same issue — diminishing returns. Step 9E + credential-rotation-schedule.md already provide the checklist. Low new leverage.

---

## Idea 5 — Push orphaned commits to PR #653 branch (operational necessity)

**Category:** operational  
**Effort:** XS  
**Confidence:** HIGH  

**Evidence:** 6 commits in detached HEAD (ddd8e77, 00940d9, cf68720, 60499dd, 430f08a, 2a76ae2) never reach origin. This run's artifacts also need pushing. PR dedup guard requires push to subconscious/run-103 branch (PR #653).

**Note:** This is Phase 8 work (commit + push), not a standalone idea. Handled in the commit/push phase regardless of which winner is chosen.
