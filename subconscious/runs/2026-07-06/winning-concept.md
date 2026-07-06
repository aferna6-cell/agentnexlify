# Run 80 Winner: Add Step 9C to Nightly SKILL.md — Brain Connector Health Check

**Date:** 2026-07-06  
**Category:** operational  
**Effort:** XS (SKILL.md edit, ~10 min)  
**Autonomous:** AUTONOMOUS-EXECUTABLE (same class as Step 9B added by run 79)  
**Confidence:** HIGH  
**Evidence source:** `brain/INGESTION-LOG.md` — 6 consecutive failure days (Jul 1–6)

---

## Recommendation

Add Step 9C to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9B. Step 9C reads `brain/INGESTION-LOG.md`, counts consecutive connector failures, and creates a deduplicated GH issue when 3+ consecutive failures are detected and no open issue with label `brain-connector-failure` exists.

---

## Why This, Why Now

Brain connectors failed for 6 consecutive days (Jul 1–6, 2026) before this run caught it. Runs 77 and 78 had no mechanism to detect this — they did not inspect `brain/INGESTION-LOG.md`. Run 79 detected the failure and filed GH #394 (credential fix, human-required). The run 80 mandate fires unconditionally: *if brain connectors still failing after next run, add Step 9C.*

**The monitoring blind spot:** the 4-day detection lag (Jul 1 failure → Jul 5 detection by run 79) is the systemic problem, not just the current credentials. Credentials will expire again. The nightly-commit-review's Jul 5 detection was *incidental* — it read the brain-refresh bot commit by chance. Step 9C makes detection unconditional and deterministic.

**AUTONOMOUS-EXECUTABLE:** same scope class as Step 9B (SKILL.md edit, adds a new bash + MCP action block). Nightly review is already authorized to edit its own SKILL.md per governance precedent (run 78 winner, implemented by run 79 commit `f09ebe9`).

**Deduplication:** Step 9C creates a GH issue ONLY IF no open issue with label `brain-connector-failure` exists. First detection → creates issue. Subsequent nights (while credentials are still broken) → finds existing open issue, logs "already escalated," skips creation. No issue spam.

---

## Implementation Sketch

### Step 9C block to add after Step 9B in `.claude/skills/nightly-commit-review/SKILL.md`

Insert after line 217 (after the Step 9B `If ALREADY EXISTS` line):

```
9C. (Brain Connector Health Check) Read last 20 lines of `brain/INGESTION-LOG.md`:
    ```bash
    tail -20 brain/INGESTION-LOG.md
    ```
    Count consecutive entries ending with `error —` or `skipped —` (from bottom up, stop on first success/missing entry).
    If consecutive_failures >= 3:
      a. Check for existing open GH issue with label `brain-connector-failure`:
         Use mcp__github__search_issues with query "repo:aferna6-cell/agentnexlify label:brain-connector-failure state:open"
      b. If NO open issue found:
         Create GH issue via mcp__github__issue_write:
           title: "Brain connector failing N consecutive days — credentials need rotation"
           body: "## Brain Connector Failure\n\n`brain/INGESTION-LOG.md` shows N consecutive days of failures:\n- **GitHub connector:** HTTP Error 403: Forbidden — token expired or scope revoked\n- **Supabase connector:** SUPABASE_ACCESS_TOKEN not set in cron environment\n\n## Impact\nAll autonomous agents (subconscious, nightly-commit-review, issue-to-pr-loop) operating on stale brain data since last successful sync.\n\n## Fix (7 min)\n1. Rotate GitHub token: Settings → Developer settings → PAT → new token with `repo` + `issues` read scopes → update in Railway Variables\n2. Set SUPABASE_ACCESS_TOKEN: Supabase dashboard → Project Settings → API → service_role key → Railway Variables\n3. Verify: `python brain/_tools/refresh_connectors.py` then `tail -5 brain/INGESTION-LOG.md`\n\nSee `subconscious/runs/2026-07-05/winning-concept.md` for detailed steps."
           labels: ["human-action-required", "brain-connector-failure", "operational", "critical"]
         Log: "GH issue created for brain connector failure (N consecutive days)"
      c. If open issue FOUND:
         Log: "brain connector failure already escalated (issue #N open) — skipping duplicate"
    If consecutive_failures < 3:
      Log: "brain connector check PASS — last entry shows success or < 3 consecutive failures"
```

### No other file changes required

The Step 9C block is self-contained. No migration, no new script file, no Python changes. The nightly SKILL.md edit is the only deliverable.

---

## What This Replaces

Nothing is removed. Step 9C adds a new detection layer on top of:
- GH #394 (human credential fix — still pending, still needed)
- Run 79 brain connector winner (still pending_human, still needed)

Step 9C ensures that if credentials expire *again* after GH #394 is resolved, the failure is caught within 24h and escalated automatically. It does not close the current GH #394 — human action is still required for the immediate fix.

---

## Run 81 Mandate

After Step 9C is added by nightly:
1. Verify Step 9C block present in `.claude/skills/nightly-commit-review/SKILL.md` (grep for "9C")
2. Verify brain/INGESTION-LOG.md last entry — if still failing after human has had 2 runs to act on GH #394, escalate further

SMS Compliance Dashboard (parking lot, 12/12 council score) is the top candidate for run 81 winner if brain connector mandate is resolved and no new mandate fires.

---

## Confidence

HIGH. Mandate fires unconditionally. Implementation is a SKILL.md edit. Deduplication prevents side effects. Closes a proven monitoring blind spot with a minimal, deterministic mechanism.

---

## Governance Corrections Applied This Run

1. **total_runs**: 79 → 80
2. **last_run**: "2026-07-05" → "2026-07-06"
3. **Run 79 winner (brain connector fix)**: status remains `pending_human` — brain connectors still failing on Jul 6 (confirmed by brain/INGESTION-LOG.md)
4. **Run 80 winner (Step 9C)**: added to active_directions as `pending_autonomous`

---

## Verification

```
Verified: brain/INGESTION-LOG.md shows 6 consecutive failures (Jul 1–6) — CONFIRMED
Verified: No open GH issue with label brain-connector-failure currently exists — PENDING (Step 9C will check at first nightly run after this commit)
Verified: Step 9C block not yet in .claude/skills/nightly-commit-review/SKILL.md — CONFIRMED (to be added by nightly-commit-review after this commit)
Verified: Step 9B present in .claude/skills/nightly-commit-review/SKILL.md — CONFIRMED (f09ebe9, run 79)
Verified: governance.json updated total_runs 79→80 — DONE (this run)
Verified: memory.jsonl run 80 entry appended — DONE (this run)
```
