# Winning Concept — Run 84 (2026-07-09)

## Recommendation
Add Step 9E to `.claude/skills/nightly-commit-review/SKILL.md` and create `ops/credential-rotation-schedule.md`. Step 9E reads the schedule, computes time since last rotation for each CI credential, and files a GH issue with `credential-rotation` label if any credential is within 14 days of its expected 90-day rotation window.

## Why This, Why Now
The 2026-07-04 credential event is the defining evidence: AUTOPILOT_GH_TOKEN and the brain connector GitHub PAT both expired on the same day, killing two independent systems simultaneously. autopilot-issue-loop had 30 consecutive failures across 5 days, stalling all 30 ai-ready issues. Brain connector failed 8+ consecutive days, leaving all autonomous agents on stale brain data.

Steps 9B (healthz), 9C (brain connector ingestion), and 9D (issue-to-pr-loop execution) are all reactive — they catch failures after they start. None of them predict expiry. Step 9E closes the fourth and final gap in the nightly monitoring triad: proactive prevention before silent failure begins.

The pattern is identical to how 9C and 9D were justified:
- 9C: Brain connector failed 8 days undetected → add reactive monitor
- 9D: Loop stalled 20+ cycles undetected → add reactive monitor
- 9E: Both systems killed by simultaneous expiry → add proactive warning

The difference is leverage: 9C/9D catch failures days after they start; 9E prevents them 14 days before they can start.

## Implementation Sketch

### 1. Create `ops/credential-rotation-schedule.md`

```markdown
# Credential Rotation Schedule

| Secret | Used by | Last rotated | Interval | Next due |
|--------|---------|-------------|---------|---------|
| AUTOPILOT_GH_TOKEN | autopilot-issue-loop.yml (GitHub Actions) | 2026-07-04 (estimated — expired this date) | 90 days | 2026-10-02 |
| Brain connector GitHub PAT | brain/_tools/refresh_connectors.py | 2026-07-04 (estimated — expired this date) | 90 days | 2026-10-02 |
| SUPABASE_ACCESS_TOKEN | brain/_tools/refresh_connectors.py | unknown — not yet set | 90 days | set first |

## How to update
After rotating any credential:
1. Set new token in environment (Railway Variables / GitHub Secrets)
2. Update "Last rotated" date in this table
3. Commit: `git commit -m "ops: rotate [credential name] (90-day cycle)"`
```

### 2. Add Step 9E to `.claude/skills/nightly-commit-review/SKILL.md`

After the existing Step 9D block (lines 239-264), insert:

```
### Step 9E — Proactive Credential Rotation Tracking

1. **Read rotation schedule:**
   - Read `ops/credential-rotation-schedule.md`
   - For each credential, compute days since last rotation
   - Flag any credential where `days_since_rotation >= (90 - 14)` = 76+ days

2. **If any credential approaching expiry (within 14 days):**
   - Search open GH issues for label `credential-rotation` via `mcp__github__list_issues`
   - If no open credential-rotation issue exists:
     - Create GH issue via `mcp__github__issue_write`:
       - Title: "Credential rotation due: [credential name]"
       - Body: credential, last rotated date, expected expiry, steps to rotate
       - Labels: `credential-rotation`, `human-action-required`
   - If open issue already exists: add comment with updated days-until-expiry

3. **If schedule file missing:**
   - Log: "Step 9E: ops/credential-rotation-schedule.md not found — skipping"
   - Do NOT create issue (schedule may be temporarily absent)

4. **Log result:**
   - Add to nightly commit log: "Step 9E: {N} credentials checked, {M} approaching expiry (within 14 days)"
```

### 3. Sequence Note
Step 9E runs after Step 9D. Both are read-only file + GH API calls + optional issue creation. Neither blocks other nightly operations.

### 4. Initial Schedule Values
Both tokens that expired on 2026-07-04 were likely created on the same date (hence simultaneous expiry). Set "last rotated" to `2026-07-04` for both after GH #399 and #394 are resolved, so next Step 9E check fires 76 days from that date (2026-09-18).

## Parallel Human Actions (URGENT)
Before Step 9E can protect the pipeline, the expired credentials must be rotated:
- **GH #399**: Rotate AUTOPILOT_GH_TOKEN in GitHub Secrets (5 min) — unblocks all 30 stalled ai-ready issues
- **GH #394**: Rotate GitHub PAT + set SUPABASE_ACCESS_TOKEN in Railway Variables (7 min) — unblocks brain connector

These are human-required. Step 9E is the structural fix; GH #399/#394 are the immediate fix.

## What This Replaces / Extends
Steps 9B/9C/9D extended the reactive monitoring triad across three pillars:
- 9B: healthz (service up/down)
- 9C: brain connector ingestion (data freshness)
- 9D: issue-to-pr-loop execution (feature delivery pipeline)

Step 9E adds a fourth pillar: proactive credential lifecycle management. First proactive (vs reactive) nightly monitor in the system.

## Confidence
**HIGH** — evidence is unambiguous (two-system simultaneous credential expiry on same date). Implementation is concrete (same GH API + SKILL.md pattern as 9C/9D). `ops/credential-rotation-schedule.md` is human-maintainable with clear update instructions. 14-day warning threshold is conservative.

## Autonomous Executable?
**YES** — SKILL.md edit + new ops file. Same class as Steps 9B/9C/9D, all of which implemented autonomously. Zero production code modified. Zero schema changes. Additive and reversible. Mark: `autonomous_executable: true`.
