# Winning Concept — Run 2026-09-16 (Run 121)

**Winner:** Step 9E Credential Expiry Escalation — Earlier Warning + GH Issue Filing
**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH
**Carry-forward count:** 2 (2nd carry-forward from run 119 winner)
**Autonomous-executable threshold:** run 122 (3rd carry-forward per Steps 9F/9G/9I/9J/9K precedent)

---

## Recommendation

Extend Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` to fire a GH issue/comment when any tracked credential has `days_remaining <= 10` (not just `days_since_rotation >= 76`), routing the alert to the credential's existing GH tracking issue rather than creating a new one.

---

## Why This, Why Now

AUTOPILOT_GH_TOKEN expires 2026-10-02 — 16 days from today. As of nightly-2026-09-15 (73 days), Step 9E correctly reported "0 approaching expiry" since 73 < 76d threshold — meaning no alert was sent even though the token is 17 days from expiry. The current Step 9E logs a warning to the nightly markdown but does NOT file a GH issue or comment on GH #399. Without a GH notification, the human has no email alert, no assignee, no audit trail. The loop will die silently on Oct 2 — replicating the exact silent-failure pattern from the Keys Koffee booking dark period (5 weeks unnoticed) and the KB pipeline gap (72+ days unnoticed). Filing a GH comment on the existing tracking issue takes one `mcp__github__add_issue_comment` call and prevents catastrophic loop death.

---

## Implementation Sketch

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block (around lines 277-300):

**Change 1: threshold logic**
```
# Current:
if days_since_rotation >= 76:
    log_warning("approaching threshold")

# New: fire 10 days before 76d threshold (= 66d since rotation)
days_remaining = 76 - days_since_rotation  # days until 76d warning threshold
days_to_expiry = 90 - days_since_rotation  # days until actual expiry
if days_remaining <= 10:
    # Search for existing credential-rotation GH issue first
    results = mcp__github__search_issues(
        query=f"repo:aferna6-cell/agentnexlify is:open label:credential-rotation {credential_name_slug}"
    )
    if results.items:
        # Comment on existing issue (e.g. GH #399 for AUTOPILOT_GH_TOKEN)
        mcp__github__add_issue_comment(
            owner="aferna6-cell", repo="agentnexlify",
            issue_number=results.items[0].number,
            body=f"**Step 9E automated alert:** {credential_name} is now {days_since_rotation}d since last rotation. "
                 f"{days_remaining}d until 76d warning threshold. Expires ~{expiry_date} ({days_to_expiry}d). "
                 f"Action required: rotate in Railway Variables / GitHub Secrets."
        )
    else:
        # Create new issue if no existing tracking issue found
        mcp__github__issue_write(
            owner="aferna6-cell", repo="agentnexlify",
            title=f"Credential rotation required (≤10d warning): {credential_name}",
            body=f"Step 9E alert: {credential_name} is {days_since_rotation}d since rotation. "
                 f"Expires ~{expiry_date}. Rotation steps: [see ops/credential-rotation-schedule.md].",
            labels=["credential-rotation", "human-action-required", "ops"]
        )
```

**Change 2: update log line**
```
# Old:
"Step 9E: {N} credentials checked, {M} approaching expiry (>=76 days), {K} unknown state"

# New:
"Step 9E: {N} credentials checked, {M} within 10d of threshold (issues filed/commented), {K} unknown state"
```

**Credentials to check:**
1. AUTOPILOT_GH_TOKEN — last_rotated: 2026-07-04, interval: 90d, threshold: 76d → days_remaining = 76-74 = 2 TODAY
2. Brain PAT — last_rotated: 2026-07-04, same state
3. SUPABASE_ACCESS_TOKEN — unknown (cannot compute days_remaining; existing unknown-state path handles this)

---

## Verification After Implementation

```bash
grep 'days_remaining' .claude/skills/nightly-commit-review/SKILL.md
grep '<= 10' .claude/skills/nightly-commit-review/SKILL.md
grep 'days_to_expiry' .claude/skills/nightly-commit-review/SKILL.md
```
All three must return results in Step 9E block.

On next nightly run: Step 9E should fire for both AUTOPILOT_GH_TOKEN and Brain PAT (74d > 66d threshold). GH #399 should receive a comment.

---

## Bonus Actions This Run (in order of priority)

1. **Comment on GH #399 directly** — since Step 9E hasn't filed yet and token expires in 16d, manually post escalation comment on GH #399 this run as a one-time bridge
2. **File GH issue for AI metering middleware** — GH #875 has 40 violations; propose middleware-level fix as architectural option for human consideration
3. **Evaluate Step 9G MCP fix for run 122** — parking lot candidate: replace `gh CLI` with `mcp__github__actions_run_trigger` in Step 9G

---

## What This Replaces

Active direction was Step 9L (AI metering nightly check — implemented run 118). That direction is implemented and working (GH #875 filed). This replaces it with the unimplemented Step 9E extension.

---

## Escalation Path

- Run 119 (winner, count=0): RECOMMEND
- Run 120 (1st carry-forward): RECOMMEND
- **Run 121 (this run — 2nd carry-forward): RECOMMEND with escalation flag**
- Run 122: autonomous-executable (3rd carry-forward per Steps 9F/9G/9I/9J/9K precedent — direct SKILL.md edit + commit without human approval)

---

## Run 122 Mandate

1. Verify `days_remaining` and `<= 10` threshold present in Step 9E (grep — SHOULD PASS if human approves or run 122 auto-implements)
2. Did Step 9E fire in nightly-2026-09-17 or later? GH #399 comment added?
3. AUTOPILOT_GH_TOKEN rotated before 2026-10-02 (expiry)?
4. Brain PAT rotation: GH issue/comment filed?
5. SUPABASE_ACCESS_TOKEN: human filled in rotation date in ops/credential-rotation-schedule.md?
6. Step 9G MCP fix: implement (replace gh CLI with mcp__github__actions_run_trigger) — run 122 winner candidate
7. GH #875 AI metering middleware proposal: GH issue filed? (bonus from run 121)
