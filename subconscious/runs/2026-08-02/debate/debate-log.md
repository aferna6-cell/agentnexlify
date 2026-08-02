# Debate Log — Run 101 (2026-08-02)

## Top 3 Ideas Ranked by Impact

1. Step 9G (operational, AUTONOMOUS-EXECUTABLE, fixes active 10-day stale gap)
2. Silent Tenant Monitoring Step 9H (operational, addresses documented 5-week miss)
3. GH #536 INTEGRATIONS_ENC_KEY escalation (operational, unblocks Gmail connector)

---

## Idea 1: Step 9G — KB Autopopulate Self-Heal Trigger

### Challenge Round 1: Is evidence strong enough?
**Attack:** Step 9G was the run 100 winner (2026-07-23). Today is 2026-08-02 — 10 days elapsed, zero implementation. Does the delayed implementation signal that this path is broken? Three nightly cycles have fired since run 100 (nightly-2026-07-29, 2026-07-30, 2026-07-31, 2026-08-01, 2026-08-02). None added Step 9G. Is this a mechanism problem?

**Defend:** Reviewing nightly-2026-07-29 through 2026-08-02: all five were either quiet ops-log cycles or LOC-guardrail-tripped cycles. The SKILL.md-edit channel requires that nightly see LOW-risk code changes eligible for auto-fix OR a specific mandate embedded in the prior winning-concept.md. Run 100's winning-concept.md specifies the exact implementation sketch, but the nightly's auto-fix pathway is triggered by code review findings, not by reading prior subconscious winning-concept files. Steps 9B–9F were all added because a subconscious run directly embedded verbatim SKILL.md block content, and nightly then applied it in the next code cycle. The correct delivery mechanism for Step 9G is NOT waiting for nightly to auto-discover it — it's direct implementation by this run (same escalation logic as Step 9F at run 99, which self-implemented on the 3rd carry-forward). This IS the 1st carry-forward for Step 9G → the correct path is: implement directly if this is a 2nd+ carry-forward, OR recommend with exact embedded content for nightly to pick up.

Given Step 9F required 3 carries before direct implementation, Step 9G gets one more pass via embedded content. Evidence is strong enough: KB stale 10 days, documented prior 63-day gap, Step 9F firing correctly, Step 9G implementation sketch complete.

**Verdict:** SURVIVES

### Challenge Round 2: Is this highest-leverage right now?
**Attack:** PR #619 just shipped 62 files of new capability. Should we focus on test coverage for the new surfaces instead? The connector_awareness `client_id` bug was an existing class; Step 9G is maintenance. Is there a higher-leverage action given the massive new code surface?

**Defend:** PR #619 passed nightly review with no bugs found. The new test coverage (2,400+ lines across 4 test files) was shipped with the PR. The nightly checked all critical invariants. Abandoning a 1-carry-forward winner for a speculative test audit is premature. The KB staleness directly impacts AI chat quality for 3 live tenants — a stale KB means the widget's vertical knowledge (coffee shop FAQ, booking hours) goes stale. Revenue-facing impact > code-health audit of already-tested new code.

**Verdict:** SURVIVES

### Challenge Round 3: Mechanism risk — workflow_dispatch permission
**Attack:** `gh workflow run kb-autopopulate.yml` requires the GH token used in nightly to have `actions:write` permission (workflow dispatch). Steps 9B–9F used `gh issue comment` and `gh label add` (issues:write). This is a different permission scope. If the nightly token lacks actions:write, Step 9G will fail silently — or worse, exit nonzero and break the nightly run.

**Defend:** The run 100 winning-concept.md's implementation sketch already addresses this: the failure path catches the nonzero exit and comments on GH #403 with the diagnostic. Failure is NOT silent — it surfaces the specific secret names needed. The permission concern is real but mitigated by the explicit failure handler. Additionally, the nightly's GH token (GITHUB_TOKEN in Actions context) does have workflow_dispatch scope in repos where the workflow file exists and the token has contents:write. The implementation uses `-R aferna6-cell/agentnexlify` to be explicit about the target repo. If the token is scoped too narrowly, the diagnostic comment is the recovery path.

**Verdict:** SURVIVES — failure path handles the permission risk

**Final verdict: SURVIVES → candidate for WINNER**

---

## Idea 2: Silent Tenant Monitoring — Step 9H Heartbeat

### Challenge Round 1: Supabase access in headless sessions
**Attack:** Supabase MCP is unavailable in headless nightly sessions. Confirmed in runs 87, 88. Any Step 9H that queries conversation counts via Supabase is dead on arrival — same mechanism block as the booking audit in run 88.

**Defend:** Two alternate approaches: (1) Use the `healthz` endpoint to check if tenants have recent activity without direct DB query. But this endpoint doesn't expose per-tenant conversation counts. (2) File a GH issue for a human-designed heartbeat, rather than autonomous execution. But then it's a planning recommendation, not a workflow improvement.

**Verdict:** WEAKENED — Supabase access mechanism is blocked for headless execution. The core insight (paying tenants need heartbeat monitoring) is valid and documented in bug-patterns.md, but the autonomous delivery path doesn't exist. Moving to parking lot as a GH issue candidate.

### Challenge Round 2: Scope drift from Step 9G
**Attack:** This is a separate operational concern from Step 9G. Taking two operational ideas in the same run violates the one-winner rule.

**Defend:** Agreed. One winner. This is parking lot material.

**Final verdict: WEAKENED → parking lot (file GH issue as bonus action)**

---

## Idea 3: GH #536 INTEGRATIONS_ENC_KEY Escalation

### Challenge Round 1: Is a comment the right action?
**Attack:** GH #536 is already tracked by nightly-2026-08-01 as a "pre-existing open issue." The nightly didn't comment on it after the July 23 deadline. Adding a comment now just extends a thread that the human isn't watching. If the human hasn't acted in 10 days, another comment is noise.

**Defend:** The differentiation is specificity: PR #619 shipped Gmail connector (2026-08-02), creating a NEW dependency on migration 176 that didn't exist when GH #536 was filed. An escalation comment explicitly connecting the PR to the blocked migration changes the urgency level from "infrastructure debt" to "active feature blocker." The information value of "Gmail OAuth will 500 until this is done" is higher than repeating the original filing.

**Challenge Round 2: Is this worth a subconscious winner slot?
**Attack:** This is a one-comment bonus action, not a strategic improvement to the system's self-improvement capability. Prior winning actions that were comments (runs 90, 91, 92) were for user-facing product blockers (referral activation, Keys Koffee booking). GH #536 is infra provisioning.

**Defend:** Agreed. This is XS bonus action material, not winner material. The value is real but not high enough to displace Step 9G.

**Final verdict: KILLED as winner → BONUS ACTION (comment on GH #536 linking PR #619)**

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| Step 9G (KB self-heal) | **SURVIVES → WINNER** | 1st carry-forward, XS proven channel, KB 10 days stale, failure path handles permission risk |
| Step 9H (tenant heartbeat) | WEAKENED → parking lot | Supabase unavailable headless; file as GH issue instead |
| GH #536 escalation | KILLED as winner → BONUS ACTION | Comment action, not strategic improvement; XS bonus |
| capabilities test audit | Not debated | Would be killed: PR's own tests comprehensive (2400+ lines) |
| GH #399 escalation | Not debated | Would be weakened: prior escalation comments already posted, nothing new to add beyond day count |
