# Winning Concept — Run 112 (2026-08-26)

## Winner: Improve Step 9J — retry `mergeable_state: "unknown"` with 30s delay

**Category:** operational
**Effort:** XS (4-line SKILL.md addition)
**Confidence:** HIGH
**Channel:** autonomous-executable (SKILL.md edit)
**Source run:** 112 (2026-08-26)

---

## Why This Won

Step 9J (Dependabot auto-merge) was implemented in run 110 (2026-08-24) and fired for the first time on 2026-08-25. Result: 19 Dependabot PRs found, 0 merged.

Root cause: Both minor/patch candidates (#679 eslint, #666 @typescript-eslint/parser) returned `mergeable_state: "unknown"` on first fetch. Step 9J has no retry logic — it skips unknown-state PRs immediately.

`mergeable_state: "unknown"` is a documented GitHub API async state: mergeability is computed lazily after first access. A re-fetch after 30s almost always resolves it. The canonical fix is one wait + one re-fetch. Without this fix, Step 9J will produce 0 merges indefinitely while GH Actions is dark (no CI means `mergeable_state` stays "unknown" or "unstable" rather than "clean" — but the initial unknown phase is still resolvable by re-fetch).

This is the difference between Step 9J being theoretical automation and actually landing security patches.

---

## Implementation (for human/nightly to apply)

**File:** `.claude/skills/nightly-commit-review/SKILL.md`

**Target:** Step 9J block, after "2. For each Dependabot PR: ... skip" logic, before step 3 (Merge eligible).

**Insert this block** between step 2 and step 3:

```
    2b. Unknown-state retry:
        Collect PRs where mergeable_state == "unknown" (not already skipped for other reasons).
        If any collected:
          Wait 30 seconds.
          Re-fetch each via mcp__github__pull_request_read.
          If mergeable_state now "clean" AND no review requests AND no blocking labels:
            Add to eligible list for step 3.
          Log: "Step 9J retry: {N} re-checked, {M} resolved to clean, {K} still unknown"
```

**Full context in SKILL.md:** Step 9J block currently reads:
```
9J. (Dependabot Auto-Merge) ...
    1. List open Dependabot PRs ...
    2. For each Dependabot PR:
       a. CI: pull_request_read → mergeable_state != "clean" → skip
       b. Review requests: requested_reviewers non-empty → skip
       c. Blocking labels: "do-not-merge" or "hold" → skip
    3. Merge eligible via mcp__github__merge_pull_request ...
    4. Log: "Step 9J: {N} checked, {M} merged, {K} skipped (CI/review/label)"
```

After implementation:
```
    2b. [retry block as above]
    3. Merge eligible (original eligible + retry-resolved) ...
    4. Log: "Step 9J: {N} checked, {M} merged, {K} skipped (CI/review/label), {P} retry-resolved"
```

---

## Verification

After SKILL.md edit: grep for "retry" in Step 9J block — must hit.
After next nightly run: check `Step 9J: ... retry-resolved` in nightly log.
Success signal: ≥1 Dependabot PR merged OR retry log shows unknown→clean resolution.

---

## Impact

- Security dep bumps (eslint #679, @typescript-eslint/parser #666) land within 24h of nightly run
- Step 9J goes from "0 merges ever" to "compounding automation" 
- 30s sleep is acceptable: nightly fires at 2:37 AM, no latency impact
- If GH Actions recovers (GH #500 resolved), `mergeable_state: "clean"` is the norm and the retry path is a no-op (cost: 0 extra API calls)

---

## Run 112 Mandate Check (vs run 111 mandate)

| Item | Status |
|------|--------|
| Pre-commit hook implemented? | UNKNOWN — run 111 winner, pending human approval. No evidence of implementation in this run. |
| Step 9K nightly result | Step 9K implemented run 110 (2026-08-25). Nightly-2026-08-26 focused on 10acf83 revenue sprint (no Step 9K log visible in digest). First full execution expected nightly-2026-08-27. |
| Annual guard audit | NOT CHECKED this run. Deferred to run 113 mandate. |
| partners.py Step 9I issue filed? | partners.py (70L, 2026-08-26 nightly) ships from 10acf83 revenue sprint. Step 9I sweeps 10 routers/nightly — will reach partners.py on next eligible nightly. GH #669 class-wide tracker covers it. |
| GH #669 PR #653 review? | OPEN, 12+ days draft. Not reviewed. |
| Step 9D escalation issue? | GH Actions dark 37+ days (GH #500). No new escalation this run. |

---

## Run 113 Mandate

1. Verify Step 9J retry block in SKILL.md (grep: "retry" in 9J section)
2. Nightly-2026-08-27: did retry log appear? Did any minor/patch Dependabot PR resolve and merge?
3. Pre-commit block_demo_role hook: implemented? (run 111 winner, human-approve channel)
4. GH #399: AUTOPILOT_GH_TOKEN still expired? (Day 48+)
5. Step 9D: file escalation comment on GH #500 if still dark (37+ days, run 112 parking lot)
6. partners.py: did Step 9I file a new issue (or dedup under GH #669)? Check nightly log.
