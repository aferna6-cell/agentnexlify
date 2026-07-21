# Debate Log — Run 100 (2026-07-21)

## Ideas Ranked by Impact (Top 3 Selected for Debate)

1. **Idea 1**: File GH issue for Migration 176 INTEGRATIONS_ENC_KEY blocker
2. **Idea 3**: Photo-quote overage billing Stripe audit
3. **Idea 2**: Apply migrations 181+182 via team peer protocol

Ideas 4 (Step 9F nightly execution gap) and 5 (platform_settings integer audit) were deprioritized — both are lower-leverage monitoring concerns compared to the top 3 which address active production risks.

---

## Debate 1: File GH Issue for Migration 176 (INTEGRATIONS_ENC_KEY)

### Challenge

**Q1: Is evidence strong enough?**
The nightly log flagged this as HIGH / ACTION REQUIRED. But it also says "Prod `integrations` table has 0 rows (verified by PR author)." If there are 0 rows, there's no urgent production risk today. Is this just precautionary?

**Q2: Is this highest-leverage right now?**
Filing a GH issue is a 5-minute task. It doesn't improve code, prevent a bug in existing code, or ship a feature. Is documentation meta-work more valuable than other code improvements?

**Q3: What could go wrong?**
Filing a GH issue for this could give false confidence that the issue is "tracked" and get deprioritized. The real action is provisioning the key and applying the migration — both need human execution in Railway.

**Q4: Has something similar been tried?**
Governance.json has no prior subconscious direction around INTEGRATIONS_ENC_KEY specifically. This is net-new.

**Q5: Too similar to current active directions?**
Active directions include GH #399 (expired AUTOPILOT_GH_TOKEN) and GH #413 (REFERRAL_REWARD_ENABLED). Those are also "human must act" items. Does this compound fatigue without resolving any?

### Defense

**A1: Evidence strength:**
Nightly explicitly labeling something HIGH / ACTION REQUIRED is the highest signal available. 0 prod rows NOW means safe window for provisioning — exactly when to act. Once GCal OAuth connects arrive (GCal integration just shipped, commit `34fa9bd`), the window closes. Acting before first OAuth connect avoids scrambling under pressure.

**A2: Leverage:**
The subconscious recommendation mechanism's whole purpose is creating durable tracking items for human-action blockers. GH issues outlast nightly logs. The current state: nightly flagged it, but nightly runs once per day and logs get archived. Without a GH issue, this warning disappears. A GH issue persists until resolved, assigns to a human, blocks the migration from being accidentally applied, and becomes searchable. Filing GH issues IS the mechanism — it's not meta-work, it's the output channel.

**A3: False confidence risk:**
True risk. Mitigation: the issue should include explicit acceptance criteria — "Issue is closed ONLY when: (1) INTEGRATIONS_ENC_KEY is in Railway prod, (2) migration 176 applied successfully, (3) oauth token round-trip verified." No false-close trap if criteria are explicit.

**A4: Novel direction:**
GH #399 and GH #413 are open but stalled — Day 18 and Day 10+ with no resolution. A third "please act" issue doesn't multiply the problem, it captures a distinct critical blocker with its own dependency chain (Railway key provisioning → apply migration → GCal OAuth). They're independent tracks.

**A5: Human fatigue:**
Better concern. But the alternative — not filing and letting Migration 176 get applied without the key — results in silent failure of every new OAuth token after first apply. That's a silent production bug with no error surfacing. The risk of inaction outweighs fatigue risk.

### Verdict: **SURVIVES — WINNER**

Strongest leverage available this run. Time-sensitive (GCal just shipped). Proven mechanism (GH issue → human action). Novel this run. Evidence top-quality (nightly HIGH flag). Zero implementation risk for the subconscious (recommendation only, no code changes).

---

## Debate 2: Photo-Quote Overage Billing Stripe Audit

### Challenge

**Q1: Is there actual evidence of a bug?**
No bug observed. This is a precautionary audit triggered by complexity of metered billing. Precaution is not evidence.

**Q2: Is Stripe metered billing actually untested here?**
Unknown without reading `backend/services/photo_quote_usage.py`. If the implementation was already tested (TDD-workflow compliance), audit is redundant.

**Q3: What's the highest risk scenario?**
Double-billing (idempotency failure) or infinite free usage (fail-open behavior). Both are serious but both are standard Stripe metered billing anti-patterns well-documented in the codebase's `backend/` conventions.

### Defense

**A1: Complexity justifies precaution:**
Metered billing is the most error-prone Stripe integration. Idempotency key bugs, daily+monthly quota interaction, fail-open behavior — any of these wrong = revenue leakage or customer harm.

**A2: We can verify:**
Read `backend/services/photo_quote_usage.py` and confirm. If clean, park it. If not, escalate.

### Verification Step (executed during debate)

Read `backend/services/photo_quote_usage.py` to check billing implementation.

**Findings:**
- Line 1: `FREE_MONTHLY_QUOTA = 500`, `OVERAGE_PRICE_USD = 0.15` — correct per spec
- `client_id` used throughout (lines 35, 68, 89, 103) — NOT `tenant_id` — invariant honored
- Idempotency key: `f"{client_id}:{quote_request_id}"` — correct (unique per quote request)
- Fail-open: `except Exception` blocks log error but return `True` (allow usage) — correct per spec ("fail-open")
- Stripe callable injectable for testing — good testability
- Daily cap (50/day) checked separately from monthly cap (500/mo) — both layers present
- `stripe_photo_quote_metered_price_id` from settings — not hardcoded

**Conclusion:** Implementation is solid. No billing bugs found.

### Verdict: **WEAKENED → Parking Lot**

No evidence of billing bug. Implementation correct on all checked dimensions. Audit idea was correct as precaution but evidence of solid implementation removes urgency. Park for future run if metered billing expands to additional features.

---

## Debate 3: Apply Migrations 181+182 via Team Peer Protocol

### Challenge

**Q1: Is the evidence strong enough to justify a subconscious pick?**
Migrations 181+182 are flagged as "DRAFT — pending peer apply" in nightly. But these are peer-apply items governed by `docs/TEAM_OPERATING_CONTRACT.md`. The team protocol is for Fable5/Codex/Kimi3 team — this subconscious is Fable5. The migrations were authored by Fable5 (this session). Under the contract, Codex or Kimi3 should be the peer applying them.

**Q2: Is this the highest-leverage action?**
Applying migrations 181+182 unblocks conversation memory tier and KB article provenance. These are shipped features that silently no-op. That's real value. But applying a migration authored by yourself (without peer review) violates the team contract.

**Q3: What could go wrong?**
Applying without peer review means no second set of eyes on the schema. The team contract exists precisely to prevent authors from applying their own migrations.

**Q4: Is this a role violation?**
Yes. Subconscious runs as Fable5. The contract says "fable5 authored; peer must apply." Acting as both author and peer breaks the audit trail.

### Defense

**A1: Speed vs. process:**
The features are shipped. The migrations are authored and reviewed (they've been in the nightly log for multiple days). Delaying further means conversation memory silently fails for every new chat message. Peer delay is blocking real user value.

**A2: Risk assessment:**
Migration 181 (`kb_article_provenance`) adds columns to an existing table — additive, low risk. Migration 182 (`conversation_message_memory`) creates a new `chat_messages` table — also additive, new table. Neither drops or modifies existing data. Risk of misapply is low.

### Verdict: **WEAKENED → Parking Lot**

The mechanism is unclear for subconscious. Applying migrations authored by this session violates team contract. The correct path is to flag these to the peer (Codex or Kimi3) via GH issue or team channel. Not the subconscious's lane to execute. Revenue value is real but mechanism is wrong for this agent.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| 1: Migration 176 GH issue | SURVIVES | **WINNER** |
| 3: Photo-quote billing audit | WEAKENED | Parking lot — already verified solid |
| 2: Migrations 181+182 apply | WEAKENED | Parking lot — wrong mechanism (peer protocol required) |
| 4: Step 9F nightly gap | Not debated | Parking lot — mandate-check item |
| 5: Platform_settings audit | Not debated | KILLED — 0 prod rows, no evidence |
