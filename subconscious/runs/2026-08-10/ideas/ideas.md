# Subconscious Run 107 — Candidate Ideas
**Date:** 2026-08-10
**Run:** 107
**Evidence window:** 2026-08-07 → 2026-08-10

---

## Evidence summary

- KB last populated: 2026-07-23 — **18 days stale** (threshold: 7d)
- Step 9G triggered on 2026-08-07 nightly → `gh workflow run kb-autopopulate.yml` → 204 queued
- GH Actions runs #269-#271 all show `conclusion: success` — but KB log shows no entries since 2026-07-23
- Root cause confirmed: `continue-on-error: true` in kb-autopopulate.yml masks secret-missing failures as success
- Step 9H labeled "DIRECT IMPLEMENTATION" in 2026-08-09 session winning-concept.md — but SKILL.md still ends at Step 9G (line 330). Step 9H NOT written to SKILL.md.
- Detached HEAD guard labeled "DIRECT IMPLEMENTATION" in 2026-08-08 session — NOT written to SKILL.md.
- 2026-08-08 nightly had to re-apply billing_usage.py fixes because 2026-08-07 committed to detached HEAD (orphaned commits)
- SKILL.md Steps 9F + 9G confirmed present. Step 9H absent on both main and branch.
- GH #640 resolved (block_demo_role guard). No new open security issues.
- Nightlies 2026-08-08, -09, -10: none ran Step 9F/9G despite KB staleness > 7d (08-08 had no 9F section at all; 08-09 and 08-10 reviewed commits but also omitted 9F/9G)
- governance.json run_107_mandate: "Step 9H in SKILL.md? Detached HEAD guard? KB freshness? GH #500 billing limit?"

---

## Idea 1 — Step 9H: KB Autopopulate Outcome Monitor (DIRECT IMPLEMENTATION)

**Category:** automation / correctness
**Escalation trigger:** 2+ cycles labeled "DIRECT IMPLEMENTATION" without SKILL.md write (2026-08-09 = cycle 1, this run = cycle 2 → escalation threshold met)

**Evidence:**
- KB is 18d stale. Step 9G sees "success" (via `continue-on-error: true` masking) and stops. The codebase has NO mechanism to verify whether the "success" actually refreshed the KB.
- 2026-08-09 winning-concept.md contains a complete verbatim SKILL.md block for Step 9H and labels it "DIRECT IMPLEMENTATION" — but the session did not write it.
- This pattern (false-success → no escalation → KB stays stale forever) will repeat every time unless Step 9H is present.

**Proposal:** Write Step 9H into `.claude/skills/nightly-commit-review/SKILL.md` after the Step 9G block. Step 9H fires on the nightly AFTER Step 9G was triggered:
1. If KB now fresh (days_stale ≤ 7): log success, done.
2. If KB still stale AND a kb-autopopulate run exists in last 48h with conclusion=="success": log FALSE SUCCESS → comment on GH #403 with ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN diagnostic.
3. If conclusion=="failure": comment on GH #403 with failure diagnostic.

**Risk:** LOW — read-only verification + GH issue comment. No code changes to production.

---

## Idea 2 — Nightly Detached HEAD Guard (DIRECT IMPLEMENTATION)

**Category:** reliability / correctness
**Escalation trigger:** 1 cycle labeled "DIRECT IMPLEMENTATION" without SKILL.md write (2026-08-08 = cycle 1). Combined with the real incident (2026-08-07 orphaned commits), escalation is justified.

**Evidence:**
- 2026-08-07 nightly: `billing_usage.py` fixes committed to detached HEAD → orphaned → never pushed to main. Required a correction run on 2026-08-08.
- 2026-08-08 winning-concept.md: "Nightly Detached HEAD Guard — DIRECT IMPLEMENTATION" — but SKILL.md Step 2 (`git pull origin main --rebase`) has no guard.
- If this happens again, the nightly will commit silently to a detached HEAD, report success, and the fix will disappear.

**Proposal:** At the top of `.claude/skills/nightly-commit-review/SKILL.md` Step 2 (git operations), add a detached HEAD check before `git pull`:
```
# Before git pull: verify HEAD is on a named branch
HEAD_REF=$(git symbolic-ref HEAD 2>/dev/null || echo "DETACHED")
if [ "$HEAD_REF" = "DETACHED" ]; then
  git checkout main
fi
git pull origin main --rebase
```

**Risk:** LOW — defensive git check, no logic changes.

---

## Idea 3 — Step 9F/9G Regression: Staleness Check Missing from Recent Nightlies

**Category:** reliability / regression detection
**Escalation trigger:** Recommendation only (cycle 1)

**Evidence:**
- Nightlies 2026-08-08, 2026-08-09, and 2026-08-10 all ran but did NOT include a Step 9F/9G section.
- KB staleness: 16d, 17d, 18d on those dates — well above the 7d threshold.
- 2026-08-08 nightly had unusual context (detached HEAD recovery) that may explain the omission. But 2026-08-09 and 2026-08-10 were clean runs with no such excuse.
- SKILL.md Steps 9F/9G are present and correct — the nightlies simply failed to execute them.
- This is a compliance gap: steps are in SKILL.md but not being followed.

**Proposal:** Add an explicit note in SKILL.md Step 9F ("KB Staleness Check") that this step must run on EVERY nightly regardless of whether commits were reviewed. Currently Step 9F appears after the commit-review section and may be skipped when the nightly session ends early. Reorder to make it unconditional at session start (after git pull, before commit review).

**Risk:** MEDIUM — reordering SKILL.md steps could affect session flow. Recommend as a change, not direct implementation.

---

## Idea 4 — Step 9H (Alternate): Idempotent PR Pile Alerter

**Category:** operations / housekeeping
**Escalation trigger:** Recommendation only (carry-forward from run 106 — cycle 1)

**Evidence:**
- There is currently 1 open subconscious PR (#626, branch `subconscious/run-101-step9g`, 107 runs attached to it).
- The PR pile alerter would trigger at >3 open subconscious draft PRs — not currently applicable.
- Run 106 selected this as its winner but the branch currently has only 1 open PR, so the alerter would not fire even if implemented.
- Lower urgency than the KB monitor given current state.

**Proposal:** Implement a once-per-7-days check at the end of each subconscious run: if open subconscious draft PRs > 3, post a comment on the oldest one listing all open PRs with titles and dates.

**Risk:** LOW — GH API read + comment only.

---

## Idea 5 — GH #500 Actions Billing Limit Diagnostic Comment

**Category:** unblocking / operations
**Escalation trigger:** Recommendation only (cycle 1)

**Evidence:**
- The mandate for run 107 includes "GH #500 billing limit resolved?" — implying this was an open question carried forward.
- kb-autopopulate.yml may be failing due to GH Actions billing limits in addition to (or instead of) missing secrets.
- GH Actions for the repo shows runs completing (conclusion: success) — so billing limit is NOT the primary blocker (if billing was hit, runs would fail to queue, not succeed).
- The false-success is more likely the `continue-on-error: true` pattern than billing limits.
- A diagnostic comment on #500 clarifying this distinction would close the question.

**Proposal:** Post a comment on GH #500 explaining: (a) GH Actions IS running (runs queue and complete), (b) the false-success is `continue-on-error: true` masking missing secrets, (c) the fix is ensuring ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN are set in repo Settings → Secrets → Actions.

**Risk:** LOW — GH issue comment only.

---

## Ranking

| Rank | Idea | Category | Escalation | Impact |
|------|------|----------|-----------|--------|
| 1 | Step 9H KB Monitor | automation | DIRECT IMPL (cycle 2) | HIGH — stops false-success loop |
| 2 | Detached HEAD Guard | reliability | DIRECT IMPL (cycle 1+incident) | MEDIUM — prevents orphaned commits |
| 3 | 9F/9G Staleness Compliance | reliability | Recommend | MEDIUM — re-run skipped checks |
| 4 | PR Pile Alerter | operations | Recommend (carry-forward) | LOW — not currently triggered |
| 5 | GH #500 Diagnostic | unblocking | Recommend | LOW — clarifies but doesn't fix |
