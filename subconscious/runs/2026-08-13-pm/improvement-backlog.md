# Run 103 — Improvement Backlog (2026-08-13-pm)

## Winner (this run)
- **Fix appointment_briefs.py: block_demo_role + ai_usage_guard + structural test** — code_health, XS effort, HIGH confidence. AUTONOMOUS-EXECUTABLE (nightly applies next cycle without human approval).

---

## Parking Lot (carry forward to run 104)

### P1: route-security-guard-audit SKILL.md (cycle 2)
**Evidence:** PR #653 open 2 days. Content written. Human hasn't merged. Run 102 winner carry-forward.
**Debate outcome:** PARKING LOT (cycle 2). Not worth re-creating content that exists in #653. Bottleneck = human merge.
**Run 104 action:** Check if #653 merged. If still open, escalate to cycle 3 with direct subconscious implementation (bypassing PR channel per escalation protocol).

### P2: Add SUPABASE_ACCESS_TOKEN to Step 9E credential tracking
**Evidence:** nightly-2026-08-13 Step 9E shows "UNKNOWN" for SUPABASE_ACCESS_TOKEN. #403 still blocked.
**Debate outcome:** WEAKENED → PARKING LOT. Redundant with existing #403 alerts. Low differentiated value.
**Run 105 action:** Elevate only if #403 still unresolved and no human salience escalation.

### P3: Update feature-build SKILL.md with 5-file standard pattern
**Evidence:** skill-discovery-2026-08-10 update proposal. e0e9be6 + 4853c31 follow pattern.
**Debate outcome:** CARRY FORWARD (uncontested, low evidence density vs winner).
**Run 104 action:** Bundle with another SKILL.md commit if execution slot available.

### P4: Create pr-backlog-triage SKILL.md
**Evidence:** 10 open PRs, 4 dependabot PRs aging 9+ days, PR debt accumulating.
**Debate outcome:** CARRY FORWARD. Not elevated — PR pile-up is a symptom of #399 blocker, not a skill gap.
**Run 104 action:** Elevate if #399 resolved and pile-up persists.

---

## Mandates for Run 104

1. **Winner execution**: Did nightly apply appointment_briefs.py fix (AUTONOMOUS-EXECUTABLE)? Check nightly log for fix commit. If not applied, check why.
2. **GH #643**: Closed after fix? Confirm.
3. **PR #653 status**: Merged or still open? If open, this is cycle 3 → escalate to direct implementation.
4. **#399 status**: Has AUTOPILOT_GH_TOKEN been rotated? Check autopilot loop success/failure count.
5. **#403 status**: Has ANTHROPIC_API_KEY been added to GH Actions secrets? KB staleness update.
6. **Dependabot PRs**: Have #649, #629, #630, #631 been merged?

---

## Frozen Ideas (never propose)
- `ai_human_handoff` — frozen, see governance.json

## Rejected Paths (do not re-propose without new evidence)
- GH #643 sketch comment (run 102) — superseded by route-security-guard-audit SKILL.md and now by appointment_briefs.py fix
- response_score.py ai_usage_guard — RESOLVED: it's a service not a router; no guard needed
