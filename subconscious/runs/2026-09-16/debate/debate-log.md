# Debate Log — Run 2026-09-16 (Run 121)

Top 3 ideas ranked by impact: Idea 1 (Step 9E), Idea 2 (Step 9G MCP fix), Idea 4 (AI metering middleware).

---

## Idea 1: Step 9E — Extend credential expiry alert (2nd carry-forward)

### Challenge
1. **Evidence strong enough?** The nightly-09-15 log shows Step 9E DID run and reported "0 approaching expiry" at 73 days — below the 76d threshold. The system is technically working correctly. Why change the threshold?
2. **Highest-leverage now?** AUTOPILOT_GH_TOKEN doesn't expire until Oct 2. The 76d threshold fires Sep 18 (in 2 days). Step 9E will alert then. Is earlier action needed?
3. **What could go wrong?** Lowering the threshold could create noisy alerts for credentials that rotate reliably. Might create duplicate comments on GH #399.
4. **Similar approach rejected?** Not rejected — this is a 2nd carry-forward, not a rejection pattern.
5. **Similar to active direction?** This IS the active direction (Step 9E). Carry-forward, not a new proposal.

### Defense
1. **Evidence strong enough:** The threshold fires at 76d — only 14 days before 90d expiry. Step 9E LOGS only; it does NOT file GH issues or comment on existing issues. GH #399 has 0 new comments from Step 9E since run 120. 3 consecutive nightlies logged the warning but human has not rotated the token. At 76d the log fires but still no GH notification to the human. The `days_remaining <= 10` threshold + GH issue filing is the missing piece, not the detection.
2. **Highest-leverage now:** AUTOPILOT_GH_TOKEN expiry Oct 2 = 16 days. Sep 18 = threshold fires = 14 days to expiry. If Step 9E at 76d only logs (no GH notification), the human won't know. Filing a GH issue creates an email notification and assignee trail. Without this, the loop dies Oct 2 silently — same failure pattern as the booking system going dark for 5 weeks.
3. **What could go wrong:** Dedup guard (search by label `credential-rotation` + credential name) prevents duplicate issues. The GH #399 comment path means: instead of creating a new issue, we comment on the existing AUTOPILOT_GH_TOKEN tracking issue. Zero new issue noise.
4. **Rejected similar?** Not applicable — this is an enhancement to existing Step 9E logic, not a new idea.
5. **Active direction confirmation:** Governance `autonomous_executable_at_run: 122` — if not approved today (2nd carry-forward), it implements autonomously at run 122.

### Verdict: SURVIVES — Carry-forward mandate and urgency (token expires 16 days) confirm winner status.

---

## Idea 2: Step 9G MCP trigger fix

### Challenge
1. **Evidence strong enough?** gh CLI has been unavailable "for 10+ runs" (run 116 confirmed) but nobody has fixed it. If this were truly urgent, wouldn't it have been prioritized before now?
2. **Is this the highest-leverage thing right now?** KB is 21d stale. Step 9G broken. But: does the KB being stale actually affect real users? How many paying tenants actively use KB-enhanced AI chat?
3. **What could go wrong?** `mcp__github__actions_run_trigger` might require permissions not available in nightly sessions. The workflow might fail for reasons other than the trigger mechanism (ANTHROPIC_API_KEY missing in GH Actions — confirmed in runs 102-104).
4. **Has this been tried?** Run 116 governance_corrections noted "Step 9G cloud fix: confirmed broken — gh CLI unavailable" and parked it. Run 120's winning concept listed it as parking lot item "Step 9G MCP fix: evaluate for run 121."

### Defense
1. **Evidence:** KB is 21d stale (above 7-day threshold). Step 9G is the dedicated mechanism to fix this. mcp__github__actions_run_trigger IS available (nightly sessions successfully use other mcp__github__ tools). The ANTHROPIC_API_KEY failure mode is separate — Step 9G already handles it by checking run status and filing a diagnostic comment if the workflow fails.
2. **Leverage:** Yes, KB staleness affects AI chat quality for all tenants. But with 3 tenants currently, impact is limited. More importantly: the fix is XS effort (1-2 line change in SKILL.md).
3. **What could go wrong:** The known blocker is ANTHROPIC_API_KEY missing in GH Actions (GH #403). Step 9G would trigger the workflow → workflow fails → Step 9G detects failure → comments on GH #403. This is better than current state (trigger never fires, GH #403 gets no updates).
4. **Previously parked:** Run 120 said "evaluate for run 121." This run is run 121. Evaluation: SURVIVES but WEAKENED because the AUTOPILOT_GH_TOKEN urgency (Idea 1) is more critical. Step 9G fix is a solid candidate for Idea 2 parking lot.

### Verdict: WEAKENED → Parking lot. Valid fix, but Step 9E's urgency (16 days to token expiry) makes it higher priority. Step 9G should be run 122 candidate if Step 9E is autonomous-implemented then.

---

## Idea 4: AI metering middleware — class-level fix for GH #875's 40 violations

### Challenge
1. **Evidence strong enough?** GH #875 was filed yesterday (2026-09-15 via nightly). Only 1 day of evidence. Is it premature to propose an architectural fix before the issue has been triaged?
2. **Highest-leverage?** There are already 40 violations tracked. Previous per-function sprint (PRs #792-#799) took several days and resolved 6. Middleware approach is more elegant but requires architectural understanding of the AI call path.
3. **What could go wrong?** Middleware-level metering could break existing per-function guards (double-counting tokens). Middleware runs before route handlers — needs to be async-safe and handle all AI call types (streaming vs. non-streaming, Managed Agents vs. direct Messages API).
4. **Has this been tried/rejected?** Not previously attempted. The per-function approach has been the pattern for all metering work to date.
5. **Scope:** Writing middleware code is an implementation, not a recommendation. Proposing the GH issue is the correct subconscious action.

### Defense
1. **Evidence sufficient:** Step 9L ran twice now (09-15: 20 violations → #871; 09-16: 40 violations → #875). The violation count INCREASED between runs (20 to 40) — this is because #871 was closed and #875 reopened with a larger scan. The class problem is confirmed: AI calls are being added faster than they're being metered per-function.
2. **Leverage is real:** 40 violations × multiple PRs each vs. 1 PR for middleware. The architectural fix permanently closes Step 9L's detection category.
3. **Counter on risks:** True — middleware double-counting is a real risk. But the proposal is to FILE A GH ISSUE, not to implement middleware directly. The GH issue captures the design proposal for human + engineering review.
4. **Not rejected:** The per-function approach has never been formally compared to a middleware approach. This would be the first time.

### Verdict: WEAKENED → Parking lot. Filing a GH issue about middleware is a good idea but it's a lower-urgency infrastructure decision compared to the token expiry emergency. Best as bonus action or run 122 candidate.

---

## Final Ranking

| Idea | Verdict | Notes |
|------|---------|-------|
| Idea 1: Step 9E 2nd carry-forward | **SURVIVES → WINNER** | Urgent (16d to expiry), 2nd carry-forward, implementation sketch ready |
| Idea 2: Step 9G MCP fix | WEAKENED → parking lot | Valid, XS effort, run 122 candidate |
| Idea 3: GH #870 batch patch script | Not debated (below top 3) | Run 123+ candidate — complex script, lower urgency than Step 9E |
| Idea 4: AI metering middleware | WEAKENED → parking lot | File GH issue as bonus action this run |
| Idea 5: Brain connector step 9C escalation | Not debated | Run 122-123 candidate — Step 9C already has 14d threshold |

## Winner: Idea 1 — Step 9E, 2nd carry-forward
