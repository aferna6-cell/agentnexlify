# Debate Log — 2026-06-15-pm

Top 3 ideas ranked by impact: Idea 1 (combined pre-commit fix), Idea 4 (JWT M3), Idea 5 (AI-to-Human Handoff).

---

## IDEA 1: Update Check 11 + Wire Check 10

### Challenge Round 1 — Evidence strength

**Attack:** Check 11 firing false positives sounds bad, but developers may have already noticed and
just ignore it. How many commits have actually seen the warning? Is there a real incident caused by
it, or is this theoretical pain?

**Defend:** Confirmed this session by direct code inspection: scripts/hooks/pre-commit lines 248-269
checks for `9900`, `15000`, `25000`, `89900` — none appear in billing.py post-repricing. Every single
commit since PR #288 (9bed342) fires this WARNING. Warning fatigue is a known, measured problem: when
developers see a constant non-actionable warning, they stop reading warnings entirely. This is the
same class of debt that caused AdminAnalyticsPage.jsx silent-catch violations to multiply (run 11
found 6 new ones because the guard wasn't there). Check 11 warning fatigue could mask a future real
billing constant regression.

Evidence for check_project_invariants exits 0: confirmed by direct execution this session ("All
project invariants passed"). This is the first clean run since run 44 / ~45 days of being blocked.
Evidence for 60+ day pending: memory.jsonl shows run 8 (2026-04-25) as first recommendation for
Check 10, with continuous references through run 57.

**Verdict:** Evidence is HIGH strength.

### Challenge Round 2 — Highest leverage?

**Attack:** This is operational hygiene, not a customer-facing feature. With paying customers now
active (PR #291), shouldn't the highest-leverage thing be something that improves customer retention
or revenue?

**Defend:** Three reasons this IS highest-leverage right now:
1. AUTONOMOUS-EXECUTABLE — doesn't require human session time or add to moratorium pending_approval.
   The moratorium has 5+ items in pending_approval; adding another would be counterproductive.
2. Closes a 60+ day debt loop. The moratorium was triggered in part by implementation lag on code
   health items. Autonomous execution is the only proven channel that reliably closes items.
3. Check 10 creates a self-healing invariant loop: future PRs that introduce from __future__, em-dash,
   or widget drift get blocked at commit time. This protects the launch hardening investments in PR
   #257 from regressing in the next sprint.

The alternative (recommending AI-to-Human Handoff again) has failed 4x and adds to moratorium count.
The alternative (JWT M3) is explicitly deferred and too complex.

**Verdict:** Highest leverage for the current context (autonomous channel, moratorium active).

### Challenge Round 3 — What could go wrong?

**Attack:** Combining two edits into one recommendation violates the atomic principle. If one part
fails, the whole recommendation fails. Is Check 10 insertion point correctly identified?

**Defend:** Both edits touch the same file (scripts/hooks/pre-commit), are both bash modifications,
and are independent of each other in the same commit. This is atomic in the deployment sense: one
commit, one PR, one review. The insertion point for Check 10 is before "# Check 11" line (~line 248),
which is unambiguous. Bash syntax: same pattern as Check 11 which already exists. Risk: LOW.

**VERDICT: SURVIVES → chosen as WINNER**

---

## IDEA 4: JWT stale plan/role claims (M3 from launch audit)

### Challenge Round 1 — Evidence strength

**Attack:** The launch-readiness audit *explicitly deferred* M3 with the note "warrant a dedicated,
unrushed change" and "deferred to its own change." If the people who wrote the audit deferred it,
why is the subconscious overriding that judgment?

**Defend:** The audit was written before PR #291 (pay gate). The deferred rationale was "token-version
check needs per-request DB read on auth hot path." That's a valid concern. But the scope of harm
changed when real paying customers went live: a plan downgrade now has financial consequences for 24h.
However — the audit also said this "fails safe" (user has EXTRA permissions, not too few). The worst
case is a cancelled user accessing paid features for 24h. Real but not severe.

**Verdict:** Evidence is MEDIUM strength — valid but explicitly deferred by domain experts.

### Challenge Round 2 — Highest leverage?

**Attack:** This requires: DB migration (new column), JWT signing changes, auth middleware changes,
backward compat (old JWTs without version field), potential mass re-sign-in. That's at minimum 3
files + migration — definitely M-effort. Would add to moratorium pending_approval count.

**Defend:** Per-request DB read is one approach. Short token TTL (1h instead of 24h) is another —
only requires config change and JWT expiry update. The TTL approach is genuinely S-effort.

**Counter:** Even TTL approach touches auth hot path. One bad config change = mass logout. Not the
right move mid-launch when the focus should be on customer retention and feature gaps.

**Verdict:** WEAKENED. Valid concern, wrong timing. Audit deferred it; subconscious should respect
that. Parking lot.

### Challenge Round 3 — Similar prior rejection?

The audit was published 2026-06-15 (today). No prior subconscious rejection. BUT: similar
"touch-the-auth-hot-path" changes have been consistently deferred across 57 runs. The pattern holds.

**VERDICT: WEAKENED → Parking Lot**

---

## IDEA 5: AI-to-Human Handoff v1

### Challenge Round 1 — Evidence strength

**Attack:** This has been "Critical" in customer-gaps.md for 60+ days without implementation. 4
prior subconscious recommendations (runs 4, 21, 29, 38) without a single customer incident driving
urgency. Is the Critical rating based on actual customer complaints or simulated gap analysis?

**Defend:** customer-gaps.md is based on 6 industry simulations, not live customer complaints.
PR #291 (pay gate) is new evidence: real paying customers means a customer who hits a complex query
the AI can't handle and doesn't get a handoff is now a cancelled subscription, not just a free-tier
dropout. That's a $19.99/month churn event instead of zero-cost.

**Counter:** True, but the *mechanism is already in active_directions (run 38)*. Recommending it
again as a new winner doesn't add implementation energy — it adds a duplicate pending item. The
bottleneck is human execution priority, not recommendation clarity.

**Verdict:** Evidence is HIGH for the customer gap, but the recommendation mechanism has failed 4x.

### Challenge Round 2 — Highest leverage?

**Attack:** Run 30 governance action explicitly stated "do not propose as winner until moratorium
exits" after the AI-to-Human Handoff GH issue mechanism failed 3x. Moratorium is still active.

**Defend:** That governance action was for the "write a GH issue" mechanism. Run 38 proposed
implementation via Agent OS (os_outbound_mirror.py already exists). That's a different mechanism.

**Counter:** Run 38 is in active_directions with status: pending_approval. Adding run 58 as another
pending_approval item makes the moratorium *worse* (pending count goes up). AUTONOMOUS-EXECUTABLE
items don't require human approval. AI-to-Human Handoff is explicitly M-effort and NOT
autonomous-executable.

**Verdict:** WEAKENED — real customer value, wrong mechanism for current moratorium context.

### Challenge Round 3 — Prior rejections?

Runs 21, 29, 38 all recommended and all failed to generate implementation. Run 30 governance action
says "do not propose as winner until moratorium exits." Moratorium is still active. Governance rule
applies.

**VERDICT: WEAKENED → Parking Lot (run 38 remains active direction)**

---

## Synthesis

Winner: **Idea 1** — Update Check 11 (remove repricing false positive) + Wire Check 10
(check_project_invariants into pre-commit). AUTONOMOUS-EXECUTABLE. HIGH confidence.

| Idea | Verdict | Disposition |
|------|---------|-------------|
| 1: Check 11 update + Check 10 wire | SURVIVES → WINNER | Active (run 58) |
| 4: JWT stale claims | WEAKENED | Parking Lot |
| 5: AI-to-Human Handoff | WEAKENED | Parking Lot (run 38 active direction stands) |
