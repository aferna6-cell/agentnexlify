# Debate Log — Subconscious Run 2026-05-05-pm (Run 14)

## Top 3 by Impact: Idea 1 (Golden Eval Harness), Idea 3 (AI Handoff), Idea 2 (Email N+1)

---

## Idea 1: Wire Golden Eval Harness to CI
**ROI:** 2.5

### Challenge
1. The eval harness tests a single AI feature (lead qualifier). Is CI coverage of one feature worth a dedicated workflow?
2. `LEAD_QUALIFIER_AGENT_ID` requires a GH Secret. If the secret isn't set, CI will skip or fail — creating a flaky gate.
3. The eval runs against a live Claude API. Monday-cron tests will consume tokens with no user benefit. Cost ~$0.10/run × 4/month = trivial, but it's non-deterministic.
4. The parking lot ROI 2.5 is self-assigned — what's the actual evidence that the lead qualifier silently regressed without anyone noticing?
5. Runs 4, 7, 8 are still pending_approval. Shouldn't the system focus on implementing those before adding new CI workflows?

### Defend
1. The lead qualifier is the first feature every tenant exercises — it's the core AI conversion funnel. A 10% silent quality drop = 10% revenue risk before anyone notices. `lead_qualifier_golden.json` provides deterministic ground truth.
2. Secret gating is standard CI pattern — env-var guard already designed in (tests.evals.__init__.py). Skip gracefully if absent; block on PR only when secret is present. No false positives.
3. Token cost: 20 test cases × ~$0.001 each = $0.02/run. Monthly: $0.08. Not a budget concern.
4. Evidence: 7854ede added the golden set and test file specifically because a prior model change silently changed classifications. The eval file exists precisely because this happened.
5. Runs 4, 7, 8 are pending_approval — system is waiting for human action on those, not more recommendations. Run 14 can legitimately recommend something new. This is a CI workflow (one file), not a competing implementation.

### Verdict: **SURVIVES**
Evidence is strong. S-effort (one workflow file). Governance explicitly queued it. Moratorium just lifted — this is the flagged first post-moratorium winner.

---

## Idea 3: AI-to-Human Handoff v1
**Run 4 winner, pending 19 days**

### Challenge
1. This was recommended 19 days ago (run 4) and still pending. Re-recommending it in run 14 doesn't add new information — it's already in active_directions.
2. M-effort (1.5-2 days) puts it outside "atomic, one-session" scope. The subconscious should recommend what a human can approve and ship quickly.
3. Customer-gaps.md shows it as Critical but "infrastructure exists" — how far is the actual implementation from what's already built?
4. Moratorium lifted because of code_health items. Recommending a M-effort feature vs. an S-effort CI gate may slow the queue further (adds another pending item rather than closing one).
5. Is this the best use of 1.5-2 dev days when 3 code_health pending items already need attention?

### Defend
1. It IS already in active_directions — re-recommending it as run 14 winner would be re-treading old ground. Valid challenge.
2. M-effort means it's NOT a trivial ask. If the system is meant to give humans an actionable single recommendation, M-effort feature work competes with S-effort CI wins.
3. The 7 industry gap is real and critical, but there's no new evidence since run 4 that made this more urgent today vs. 19 days ago.

### Verdict: **KILLED (re-recommendation of active_directions, M-effort, no new evidence)**
Already queued. No new urgency signal. Pending queue should shrink before growing.

---

## Idea 2: Fix email_sequences N+1 Queries
**ROI: 2.3, GH #112**

### Challenge
1. GH #112 was opened 3 days ago (2026-05-02). The email automation feature is relatively new — how many tenants are actually hitting list_enrollments at scale?
2. N+1 at 1000 enrollments = 1001 queries. Supabase connection pool handles this fine at current scale. This is a future problem, not a today problem.
3. M-effort refactor involves restructuring two query functions in a 1255-line router. Risk of introducing a bug in a feature that works today.
4. The issue is already tracked in GH #112 with full documentation — it doesn't need a subconscious recommendation to keep it visible.
5. Is there evidence of actual slow queries or timeouts from this N+1 pattern today?

### Defend
1. Current tenant count is growing. N+1 is a latency timebomb — better to fix at M-effort now than at emergency speed when first large tenant onboards.
2. The `.in_()` fix is well-understood in Supabase Python client. Not a novel refactor.
3. Correct challenge: issue is tracked, feature is low-adoption, and it's M-effort.

### Verdict: **WEAKENED**
Real issue but not urgent. Feature adoption hasn't scaled to where N+1 hurts. Issue #112 already tracks it. Can wait for email sprint. Better candidates exist.

---

## Synthesis

| Idea | Verdict |
|------|---------|
| Wire golden eval harness to CI | SURVIVES → **WINNER** |
| AI-to-Human Handoff v1 | KILLED (re-recommendation, no new evidence) |
| Fix email N+1 | WEAKENED (valid, not urgent, tracked in GH) |
| Fix KB wikilinks | Did not reach top 3 (ROI 1.4 approx) |
| Extract _process_pending_sends | Did not reach top 3 (ROI 1.8, tracked in GH #113) |

**Winner: Wire Golden Eval Harness to CI**

Evidence: 7854ede added the harness specifically after a silent regression. S-effort (one GitHub Actions YAML). ROI 2.5 — highest in parking lot. Governance explicitly flagged it as "first post-moratorium winner." Onboarding V2 sprint is active — new agents may affect lead classifier behavior; weekly eval catch will surface drift before it reaches tenants.

**Bonus: Complete Run 8 (check_project_invariants.py wiring)**
Em-dash blocker cleared today (8f680e8). check_project_invariants.py passes all 6 checks with zero violations. Wiring it into pre-commit is S-effort (one bash call addition). This closes run 8 — drops pending from 3 → 2. Moratorium re-trigger threshold: 3. Including as bonus step keeps us below the threshold.
