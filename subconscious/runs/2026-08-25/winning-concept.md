# Winning Concept — Run 110 (2026-08-25)

## Recommendation
Add Step 9K to `.claude/skills/nightly-commit-review/SKILL.md` — a stale-subconscious-PR closer that auto-closes superseded draft PRs and escalates unapproved ones older than 21 days.

## Why This, Why Now
Run 110 mandate explicitly named Step 9K as a candidate if subconscious PR count ≥ 3 — confirmed at 4 open drafts (#575 32d, #626 22d, #653 12d, #674 1d). PRs #575 and #626 are superseded by direct implementations (Steps 9B/9G shipped in runs 78 and 101 respectively); they are noise that dilutes the signal of the actionable PR (#674). Every nightly that doesn't close these gives the owner 4 PRs to mentally parse when only 1 needs attention. Step 9K permanently solves this: after the first nightly run it auto-closes the superseded PRs and thereafter keeps the queue at ≤ 1-2 per cycle. The autonomous-executable channel (SKILL.md edit) is proven for this class of change (Steps 9F/9G/9I/9J all shipped this way).

## Implementation Sketch

**File to edit:** `.claude/skills/nightly-commit-review/SKILL.md`

**Insertion point:** After Step 9J's log line (`9J: {N} checked, {M} merged, {K} skipped`), before `10. Commit report`.

**Block to add:**
```
9K. (Stale Subconscious PR Cleanup) Manage open draft subconscious PRs:
    1. List open PRs with head branch matching "subconscious/*" OR title prefix "subconscious:"
       via mcp__github__list_pull_requests (state="open")
       If 0 found: log "Step 9K: 0 subconscious PRs open — skip" and continue
    2. For each subconscious PR:
       a. Read governance.json active_directions — find matching title
       b. If entry found AND implemented=true AND PR age > 7 days:
          → Close PR via mcp__github__update_pull_request (state="closed")
          → Post comment: "This subconscious draft has been superseded — the recommendation
            was implemented directly (per governance.json). Closing to reduce PR noise.
            Artifacts preserved in subconscious/runs/."
          → Log "Step 9K: closed #{PR_number} (superseded by direct implementation)"
       c. If PR age > 21 days AND no implemented match in governance.json:
          → Post comment: "This subconscious draft is {age}d old and still open.
            Action needed: review winning-concept.md and either approve or close."
          → Log "Step 9K: escalated #{PR_number} ({age}d, awaiting review)"
       d. Otherwise: log "Step 9K: skipped #{PR_number} ({age}d, not yet superseded)"
    3. Log summary: "Step 9K: {N} checked, {M} closed (superseded), {K} escalated, {J} skipped"
```

**Current expected outcomes on first nightly run:**
- #575 (32d): governance has Steps 9B/9G implemented → **auto-close**
- #626 (22d): governance has Step 9G implemented → **auto-close**
- #653 (12d): block_demo_role middleware → no implemented=true in governance → **skip** (under 21d)
- #674 (1d): Step 9J → has implemented=true → but 1d old → **skip** (under 7d grace)

After first run: queue drops from 4 to 2. By day 7 grace, #674 may also close if confirmed implemented.

## What This Replaces
Run 109 winner (Step 9J) is fully implemented and verified. Step 9K is the next logical step in the same proven channel, addressing a distinct gap (PR accumulation vs security dependency hygiene).

## Confidence
**HIGH** — evidence is direct (4 open PRs, run 110 mandate), mechanism is proven (SKILL.md-edit channel Steps 9F/9G/9I/9J), risk is neutralized (implemented=true guard prevents premature close of substantive PRs).

---

## Run 111 Mandate

1. **Step 9K present in SKILL.md?** `grep 'Step 9K' .claude/skills/nightly-commit-review/SKILL.md` — SHOULD PASS if human approves this winner (or 1st-carry-forward autonomous escalation fires).
2. **First nightly with Step 9K:** how many PRs closed? How many escalated? Log line: `Step 9K: {N} checked, {M} closed, {K} escalated, {J} skipped`.
3. **PR #575 and #626 closed?** Confirm both closed by Step 9K or manually.
4. **Step 9J results improving?** Are minor/patch Dependabot PRs reaching `mergeable_state: clean` after GH Actions resume?
5. **GH #669 (block_demo_role class-wide):** any human action on PR #653 or alternative fix?
6. **KB staleness:** still 33d+? Has human rotated ANTHROPIC_API_KEY in GH Actions?
7. **memory.jsonl dedup bug** (run 110 parking lot): if no higher-leverage idea, pick this as run 111 winner.
