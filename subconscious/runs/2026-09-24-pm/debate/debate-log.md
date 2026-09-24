# Debate Log — Run 2026-09-24-pm (Run 129)

## Top 3 Contenders

1. **Idea 1**: Step 9J Priority Queue Fix (run 128 carry-forward)
2. **Idea 2**: Step 9G KB Failure Diagnostics
3. **Idea 3**: Step 9M AI Metering Trend Tracking

---

## Idea 1: Step 9J Priority Queue Fix

### FOR
- Run 128 governance mandate: active_direction confirmed, 1st carry-forward fires now
- XS effort: two parameters added to one function call (`sort: 'created'`, `direction: 'asc'`, `perPage: 5`)
- Autonomous-executable: qualifies for nightly-commit-review implementation (SKILL.md edit, 0-code risk)
- Concrete evidence: 7+ consecutive nightlies show 17/19 Dependabot PRs skipped; oldest PRs (#885-#891) carry CVE-age risk
- Zero ambiguity on mechanism: `sort: 'created', direction: 'asc', perPage: 5` on `search_pull_requests`
- Already absent from SKILL.md (grep=0 confirmed this run) — not a duplicate
- Incremental improvement to existing step, no new step required
- Zero human approval needed under autonomous-executable channel (3 carries → eligible; this is 1st carry so escalation path clear for nightly)

### AGAINST
- Only affects ~5 PRs/run — still doesn't fix the core token budget depletion causing skips
- Doesn't address why 17/19 are skipped; root cause is token budget, not sort order
- Processing 5 oldest PRs is better than 5 newest PRs but still leaves 12-14 unprocessed

### Verdict: **SURVIVES — STRONG**
The against arguments are real but orthogonal: priority queue ordering is strictly better than random regardless of budget constraints. Root cause (token budget) is a separate issue. This delivers guaranteed improvement within the current constraint. Run 128 governance mandate applies.

---

## Idea 2: Step 9G KB Failure Diagnostics

### FOR
- KB is 29 days stale — this problem is real and worsening
- Step 9G gh→MCP fix (run 126) already works — trigger fires but fails silently
- Polling kb-autopopulate.yml run status 30s after trigger is a known MCP pattern
- Converts silent failure into actionable GH #403 comment with exact error
- Reduces human diagnosis time from 10+ min to 0
- S effort: ~10 lines in SKILL.md Step 9G block
- Doesn't require fixing ANTHROPIC_API_KEY — just surfaces the error clearly

### AGAINST
- GH #403 already has multiple nightly comments about KB staleness — adding one more may create comment noise
- The actual fix requires human action (adding ANTHROPIC_API_KEY to GH Actions secrets) regardless
- Polling 30s after trigger requires the trigger to have fired AND kb-autopopulate.yml to have started — timing could be unreliable
- S effort vs XS: Step 9J is objectively smaller and faster to implement

### Verdict: **SURVIVES — MODERATE**
Genuine value but lower than Step 9J. The polling approach adds 30s of wall-clock wait to every Step 9G run. And adding another comment to GH #403 risks "comment spam" that desensitizes the human. Value is real but delivery mechanism has friction. Idea 4 (consolidated diagnostic comment) actually addresses GH #403 more directly without modifying SKILL.md.

---

## Idea 3: Step 9M AI Metering Trend Tracking

### FOR
- GH #827 has 45 open violations — without trend data, no way to know if improving or regressing
- Simple mechanism: count open issues with label `billing + ai-ready`, compare to stored count, log delta
- State file (subconscious/state/ai_metering_trend.json) is a pattern already used by the system
- Week-over-week alert on GH #827 prevents silent regression backlog growth
- S effort: new step added at end of nightly SKILL.md, low coupling

### AGAINST
- Issues with label `billing + ai-ready` may not cleanly proxy for violations (some may be closed/resolved, label may get stale)
- The 45 violations were filed by Step 9L — if Step 9L keeps filing, count goes UP even without regression (new coverage is good)
- A rising count could mean MORE coverage detected (positive) not MORE violations (negative) — trend could be misleading
- No baseline established yet — first run would just record count with no delta to report
- More novel than Step 9J; requires new state file, new step in SKILL.md, more moving parts

### Verdict: **WEAKENED**
The proxy metric (open issues with billing+ai-ready) conflates new detections with actual regressions. Until Step 9L's detection rate stabilizes, trend data will be noisy. Better to wait until the 45 open violations are resolved before adding a trend tracker. Premature instrumentation.

---

## Winner Selection

| Idea | Verdict | Effort | Mandate |
|------|---------|--------|---------|
| Step 9J Priority Queue | SURVIVES STRONG | XS | Run 128 governance |
| Step 9G KB Diagnostics | SURVIVES MODERATE | S | New |
| Step 9M Trend Tracking | WEAKENED | S | New |

**WINNER: Idea 1 — Step 9J Priority Queue Fix**

Rationale: Run 128 governance mandate, XS effort, autonomous-executable via nightly, zero ambiguity on implementation, confirmed absent from SKILL.md. This is the clearest possible carry-forward: the previous run identified it, debated it, won, and now 1st-carry escalation makes it the priority. Idea 2 (KB Diagnostics) is worth implementing in a future run once this is executed and cleared.
