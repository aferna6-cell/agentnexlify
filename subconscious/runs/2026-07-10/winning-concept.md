# Winning Concept — Run 86 (2026-07-10)

**Date:** 2026-07-10
**Run:** 86
**Category:** operational
**Effort:** XS
**Confidence:** HIGH
**Status:** AUTONOMOUS-EXECUTABLE

---

## 2nd-Miss Escalation Note

Run 84 (2026-07-09) recommended Step 9E. Nightly missed it. Run 85 re-verified it was still missing.
Nightly missed it again. This is the 2nd consecutive miss.

Root cause identified by comparing all Steps 9B/9C/9D vs run 84 Step 9E:

| Step | winning-concept.md format | Implemented? |
|------|--------------------------|-------------|
| 9B | Embedded exact script content for `ops/monitoring/healthz-alert.sh` | Yes — 1 cycle |
| 9C | Embedded exact SKILL.md block text | Yes — 1 cycle |
| 9D | Embedded exact SKILL.md block text | Yes — 1 cycle |
| 9E (run 84) | Prose description only — "create schedule.md… add Step 9E block…" | No — 2 misses |

Fix applied in this document: **EMBEDDED EXACT FILE CONTENT** for both deliverables below.
The nightly has zero ambiguity. It reads this file and applies the embedded content verbatim.

---

## Recommendation

Add Step 9E to `.claude/skills/nightly-commit-review/SKILL.md` and create `ops/credential-rotation-schedule.md`.

Step 9E reads the schedule nightly, computes days since last rotation for each CI credential, and files a GH issue with `credential-rotation` label if any credential is ≥76 days since last rotation (14-day warning before 90-day expiry).

**AUTONOMOUS-EXECUTABLE** — same class as Steps 9B/9C/9D (SKILL.md edit + ops file creation). Zero production code modified. Zero schema changes. Additive and reversible.

---

## Why This, Why Now

The 2026-07-04 credential event: AUTOPILOT_GH_TOKEN + brain connector GitHub PAT both expired the same day. Two independent systems failed simultaneously. autopilot-issue-loop had 30 consecutive failures across 5 days. Brain connector failed 8+ consecutive days.

Steps 9B/9C/9D are reactive — they catch failures after they start. Step 9E is the first proactive monitor: 14-day warning gives human time to rotate before failure begins.

This has missed 2 consecutive nightly cycles (runs 84 and 85 recommendations both skipped). Embedded content in this document is the structural fix for the miss pattern.

---

## Deliverable 1 — Create `ops/credential-rotation-schedule.md`

**EMBEDDED FILE CONTENT — write this verbatim:**

```
# Credential Rotation Schedule

| Secret | Used by | Last rotated | Interval | Next due |
|--------|---------|-------------|----------|---------|
| AUTOPILOT_GH_TOKEN | autopilot-issue-loop.yml (GitHub Actions → GitHub Secrets: aferna6-cell/agentnexlify) | 2026-07-04 (estimated — expired this date) | 90 days | 2026-10-02 |
| Brain connector GitHub PAT | brain/_tools/refresh_connectors.py (local cron + Railway) | 2026-07-04 (estimated — expired this date) | 90 days | 2026-10-02 |
| SUPABASE_ACCESS_TOKEN | brain/_tools/refresh_connectors.py (Railway cron env) | unknown — not yet set in environment | 90 days | set first, then track |

## How to update this file
After rotating any credential:
1. Set new token in environment (Railway Variables / GitHub Secrets)
2. Update "Last rotated" date in this table
3. Update "Next due" = last_rotated + 90 days
4. Commit: `git commit -m "ops: rotate [credential name] (90-day cycle)"`

## Notes
- AUTOPILOT_GH_TOKEN: set in GitHub Secrets under repo aferna6-cell/agentnexlify. GH #399 tracks rotation.
- Brain connector PAT: set in Railway Variables (or local cron env). GH #394 tracks rotation.
- SUPABASE_ACCESS_TOKEN: set in Railway Variables for brain connector. Voyage API key also required.
- Step 9E in .claude/skills/nightly-commit-review/SKILL.md reads this file nightly.
  Files a GH issue if any credential is >=76 days since last rotation (14-day warning before 90-day expiry).
```

**Commit:** `ops(credentials): add credential-rotation-schedule.md [auto-nightly-YYYY-MM-DD]`

---

## Deliverable 2 — Add Step 9E to `.claude/skills/nightly-commit-review/SKILL.md`

**Location:** Insert after Step 9D block (after the line reading `    Log result: "Step 9D: {N} ai-ready issues, {M} stalled, loop last ran {timestamp}, status: {PASS|STALLED}"`) and before step `10. Commit report`.

**EMBEDDED BLOCK TEXT — insert this verbatim:**

```
9E. (Proactive Credential Rotation Tracking) Check credential rotation schedule for approaching expiries:
    1. **Check if schedule file exists:**
       ```bash
       ls ops/credential-rotation-schedule.md 2>/dev/null || echo "MISSING"
       ```
       If MISSING: log "Step 9E: ops/credential-rotation-schedule.md not found — skipping" and continue to step 10.
    2. **Read schedule and compute days since last rotation:**
       Read `ops/credential-rotation-schedule.md` line by line.
       For each credential row: parse "Last rotated" date field.
       Compute days_since_rotation = (today - last_rotated_date).
       Flag as approaching_expiry if days_since_rotation >= 76 (= 90 days - 14-day warning window).
       If last_rotated is "unknown" or "not yet set": flag as unknown_state, log separately.
    3. **If any credential approaching expiry (days_since_rotation >= 76):**
       a. Search open GH issues with label `credential-rotation`:
          `mcp__github__list_issues` with labels: ["credential-rotation"], state: OPEN
       b. If NO open credential-rotation issue exists:
          Create GH issue via `mcp__github__issue_write`:
            title: "Credential rotation due in ≤14 days: [credential name(s)]"
            body: credential name, last_rotated date, days_since_rotation, expected expiry, rotation steps
            labels: ["credential-rotation", "human-action-required"]
       c. If open credential-rotation issue FOUND:
          Add comment via `mcp__github__add_issue_comment` with updated days_since_rotation.
    4. **Log result:**
       Add to nightly commit log: "Step 9E: {N} credentials checked, {M} approaching expiry (>=76 days), {K} unknown state"
```

**Commit:** `ops(nightly): add Step 9E credential rotation tracking [auto-nightly-YYYY-MM-DD]`
After commit: update `governance.json` active_directions Step 9E entry status → `implemented`.

---

## Execution Order

1. Create `ops/credential-rotation-schedule.md` from Deliverable 1 embedded content
2. Add Step 9E block to SKILL.md from Deliverable 2 embedded content
3. Commit each file separately (one commit per file per nightly guardrail)
4. Update governance.json Step 9E status → `implemented`

Both actions are LOW-risk per nightly classification:
- `ops/credential-rotation-schedule.md` — new file in `/ops/` (not FORBIDDEN)
- SKILL.md edit — same class as Steps 9B/9C/9D (all implemented autonomously)

---

## Parallel Human Actions (URGENT — still outstanding)

Before Step 9E can protect the pipeline, expired credentials must be rotated:
- **GH #399**: Rotate AUTOPILOT_GH_TOKEN in GitHub Secrets (5 min) — unblocks all stalled ai-ready issues
- **GH #394**: Rotate GitHub PAT + set SUPABASE_ACCESS_TOKEN in Railway Variables (7 min) — unblocks brain connector

These are human-required. Step 9E is the structural prevention fix; GH #399/#394 are the immediate recovery fix.

---

## What This Replaces

Steps 9B/9C/9D extended the reactive monitoring triad:
- 9B: healthz (service up/down)
- 9C: brain connector ingestion (data freshness)
- 9D: issue-to-pr-loop execution (feature delivery pipeline)

Step 9E adds the fourth pillar: proactive credential lifecycle management. First proactive (not reactive) nightly monitor. Closes the last autonomous pipeline gap identified by runs 84-86.

---

## Confidence

**HIGH** — evidence unambiguous (two-system simultaneous credential expiry 2026-07-04). Implementation concrete (same GH API + SKILL.md pattern as 9C/9D). Embedded content eliminates the only known miss-pattern (prose-description vs embedded-content). `ops/credential-rotation-schedule.md` is human-maintainable with clear update instructions.

---

## Run 87 Mandate

1. Verify `ops/credential-rotation-schedule.md` was created by nightly-2026-07-11
2. Verify Step 9E block present in `.claude/skills/nightly-commit-review/SKILL.md`
3. Verify Step 9E first execution ran and logged result (check nightly commit log)
4. If BOTH confirmed: promote Lead Source Analytics Dashboard (subconscious/runs/2026-07-09-pm/winning-concept.md) as run 87 winner — create GH issue with `ai-ready` label
5. If EITHER missing: this is the 3rd consecutive miss — escalate to human-action-required GH issue, file under label `subconscious-unexecuted`, body: "3 consecutive nightly misses on Step 9E. Autonomous execution path broken. Human must manually execute Deliverables 1 and 2 from subconscious/runs/2026-07-10/winning-concept.md."
