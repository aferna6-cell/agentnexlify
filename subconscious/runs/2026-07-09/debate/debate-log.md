# Debate Log — Run 84 (2026-07-09)

## Top 3 Ideas Entering Debate

1. **Idea 1**: Step 9E — Proactive Credential Rotation Tracking (SURVIVES → WINNER)
2. **Idea 2**: Lead Source Analytics Dashboard (WEAKENED → parking lot)
3. **Idea 3**: SMS Compliance Dashboard Direct Delivery (KILLED)

---

## Round 1: Does Each Idea Address the Run's Most Critical Gap?

### Idea 1 (Step 9E)
**FOR:** The 2026-07-04 event is the defining evidence of this run. Two independent systems (autopilot-issue-loop + brain connector) failed simultaneously because their tokens were created the same day. Steps 9B/9C/9D are reactive monitors — they catch failures AFTER they happen. Step 9E is the only idea that prevents the failure before it occurs. 14-day advance warning gives the human a rotation window. The autonomous mechanism is identical to Steps 9C and 9D, both of which implemented flawlessly.

**AGAINST:** Credential rotation schedules require humans to keep them updated. If last-rotation date isn't maintained in `ops/credential-rotation-schedule.md`, the step fires false positives (token hasn't actually rotated) or false negatives (date wrong). The schedule is only as accurate as human discipline.

**VERDICT:** Counter-argument is valid but weak. False positive = extra GH issue, small cost. False negative = same as current state, no regression. Net: Step 9E is strictly better than no Step 9E. SURVIVES.

### Idea 2 (Lead Source Analytics)
**FOR:** Cross-industry, Low Effort, HIGH impact. Recharts installed, `source` column exists. Customer-facing value is real. Was the run 83 parking lot item most likely to promote.

**AGAINST:** Run 84 mandate explicitly conditions this on "pipeline confirmed healthy." Pipeline is definitively NOT healthy: autopilot-issue-loop has 30 consecutive failures, brain connector is down 8+ days, GH #399 and #394 are unresolved. Implementing a customer dashboard feature while the delivery pipeline is stalled violates the mandate's conditional logic. No point promoting a feature via a broken loop.

**VERDICT:** Mandate condition unmet. WEAKENED — parking lot. Promote to run 85 if GH #399 resolved.

### Idea 3 (SMS Dashboard Direct Delivery)
**FOR:** GH #385 has been waiting 25+ days. Paste-ready code exists. Customer feature.

**AGAINST:** The stall isn't a feature-difficulty problem. It's a credential problem. GH #399 (rotate AUTOPILOT_GH_TOKEN, 5 min human action) unblocks the loop, which then picks up #385 AND all 29 other stalled ai-ready issues automatically. Direct delivery of SMS Dashboard bypasses the loop entirely, leaving all other 29 issues still stalled. It's treating the symptom on one issue when treating the root cause (credential rotation) resolves all 30. Step 9E's credential rotation schedule also reduces probability of this happening again.

**VERDICT:** KILLED. Root cause fix (Step 9E proactive tracking) + human credential rotation (GH #399) is the correct path. Direct delivery is less efficient and doesn't compound.

---

## Round 2: Is Step 9E Truly Autonomous?

**Claim:** AUTONOMOUS-EXECUTABLE — same class as Steps 9B/9C/9D.

**Test against precedent:**
- Step 9B: Added SKILL.md block + wrote ops/monitoring/healthz-alert.sh. Both autonomous. ✓
- Step 9C: Added SKILL.md block. Autonomous. ✓
- Step 9D: Added SKILL.md block. Autonomous. ✓ Implemented by nightly e8b2ddc.

Step 9E requires:
1. Create `ops/credential-rotation-schedule.md` — new ops file, same class as healthz-alert.sh in Step 9B ✓
2. Add Step 9E block to `.claude/skills/nightly-commit-review/SKILL.md` — same class as Steps 9C/9D ✓

Both operations: additive, reversible, zero production risk. Nightly review can execute without human approval.

**CONFIRMED AUTONOMOUS-EXECUTABLE.** 

---

## Round 3: Is the Step 9E Design Sound?

**Concern:** How does nightly know the last-rotation date? Humans could forget to update `ops/credential-rotation-schedule.md`.

**Design answer:** Step 9E reads the schedule file and computes `(today - last_rotation_date) >= (rotation_interval - 14_days)`. If a human rotates the token and doesn't update the file, Step 9E will eventually fire a false-positive GH issue. The correct response to a false-positive is to UPDATE the schedule file — which reinforces the habit of maintaining it. Over time, the mechanism trains the human to keep the schedule accurate.

The schedule file also serves as documentation — first time this project has a canonical list of all CI secrets and their expected refresh cycle. Operational value independent of the nightly step.

**VERDICT:** Design is sound. File serves dual purpose: nightly check input AND credential inventory.

---

## Final Verdicts

| Idea | Verdict | Reason |
|------|---------|--------|
| Idea 1: Step 9E | **WINNER** | Closes proactive prevention gap; autonomous; high confidence; addresses root cause of run's defining event |
| Idea 2: Lead Source Analytics | **WEAKENED → parking lot** | Mandate condition unmet (pipeline not healthy); promote to run 85 |
| Idea 3: SMS Dashboard Direct Delivery | **KILLED** | Root cause fix unblocks 30 issues; direct delivery only unblocks 1 |
| Idea 4: INGESTION-LOG.md in Phase 2 | Not debated — redundant with Step 9C |
| Idea 5: Dependabot batch merge | Not debated — human-only housekeeping |
