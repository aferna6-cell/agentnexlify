# Winning Concept — Run 2026-09-16-pm (Run 121)

**Winner:** Step 9E Credential Expiry Escalation — 2nd Carry-Forward → Autonomous-Executable at Run 122
**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH
**Carry-forward count:** 2 (2nd carry-forward; was 1st carry-forward in run 120)
**Autonomous-executable threshold:** 3 consecutive carries → run 122 fires at run 123

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` tracks credential rotation age. Current logic:
- Fires when `days_since_rotation >= 76`
- Logs to nightly markdown file only
- Does NOT file a GH issue
- Does NOT comment on existing rotation tracking issue

Result: 5+ consecutive nightly runs (Sep 11 × 2, Sep 13, Sep 14, Sep 16) logged "AUTOPILOT_GH_TOKEN approaching threshold" with zero human action. No GH issue = no email notification = no assignee = no audit trail.

**Current state (2026-09-16):**
- AUTOPILOT_GH_TOKEN: 74 days since rotation (threshold 76d, interval 90d). Crosses threshold in ~2 days. Expires 2026-10-02 (16 days away).
- Under the NEW `days_remaining <= 10` threshold we're proposing, the token crossed the trigger threshold 8 days ago (74d > 66d). We've already missed 8 days of warning opportunity.
- Brain connector GitHub PAT: also last rotated 2026-07-04, same expiry profile.
- SUPABASE_ACCESS_TOKEN: unknown state (last_rotated not set).
- GH #399: existing rotation tracking issue. NOT receiving automated comments.

Grep confirms Step 9E does NOT currently file GH issues:
- `grep 'days_remaining' SKILL.md` → 0 results in Step 9E block
- `grep '<= 10' SKILL.md` → 0 results
- `grep 'add_issue_comment' SKILL.md` → 0 results in Step 9E block

---

## Implementation

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block.

**Change threshold logic:**
```
# Current (fires too late, no issue filed):
if days_since_rotation >= 76:
    log_warning("approaching threshold")

# New (fires 10 days before threshold, files/comments on GH issue):
days_remaining = threshold_days - days_since_rotation  # threshold_days = 76
# This fires when days_since_rotation >= 66 (10 days before 76d threshold)
if days_remaining <= 10:
    # Dedup: search open issues by label "credential-rotation" + credential name
    # If existing open issue found: add comment with current days_remaining
    # If no open issue: create new issue with labels ["credential-rotation", "human-action-required", "ops"]
    search_result = mcp__github__search_issues(
        query=f"repo:aferna6-cell/agentnexlify is:open label:credential-rotation {credential_name}")
    if search_result.total_count > 0:
        existing_issue = search_result.items[0]
        mcp__github__add_issue_comment(
            owner="aferna6-cell", repo="agentnexlify",
            issue_number=existing_issue.number,
            body=f"Step 9E automated update: {credential_name} now at {days_since_rotation}d since rotation. "
                 f"{days_remaining}d remaining before {threshold_days}d threshold. "
                 f"Expires ~{expiry_date}. Action required: rotate in Railway → update GitHub Secrets.")
    else:
        mcp__github__issue_write(
            owner="aferna6-cell", repo="agentnexlify",
            title=f"Credential rotation required: {credential_name}",
            body=f"## Credential rotation required\n\n"
                 f"**Credential:** {credential_name}\n"
                 f"**Days since rotation:** {days_since_rotation}\n"
                 f"**Days remaining before threshold:** {days_remaining}\n"
                 f"**Threshold:** {threshold_days} days\n"
                 f"**Expiry date:** ~{expiry_date}\n\n"
                 f"## Action required\n\n"
                 f"1. Rotate the credential in Railway (or wherever stored)\n"
                 f"2. Update corresponding GitHub Secrets\n"
                 f"3. Update `ops/credential-rotation-schedule.md` with new `last_rotated` date\n"
                 f"4. Comment on this issue confirming rotation complete\n\n"
                 f"Filed automatically by Step 9E credential rotation monitor.",
            labels=["credential-rotation", "human-action-required", "ops"])
```

**Credentials to check:**
1. AUTOPILOT_GH_TOKEN — last_rotated: 2026-07-04, interval: 90d, threshold: 76d
2. Brain PAT — last_rotated: 2026-07-04, interval: 90d, threshold: 76d
3. SUPABASE_ACCESS_TOKEN — last_rotated: unknown (human must fill in)

**Dedup guard (critical):** Search by label `credential-rotation` + credential name slug. GH #399 is the existing AUTOPILOT_GH_TOKEN rotation issue — comment on it rather than creating a duplicate.

---

## Verification After Implementation

```bash
grep 'days_remaining' .claude/skills/nightly-commit-review/SKILL.md
grep '<= 10' .claude/skills/nightly-commit-review/SKILL.md
grep 'add_issue_comment' .claude/skills/nightly-commit-review/SKILL.md
```
All three must return results in Step 9E block.

Next nightly run: Step 9E should fire for AUTOPILOT_GH_TOKEN (74d > 66d threshold). GH #399 should receive a comment.

---

## Run 122 Mandate

1. Verify `days_remaining` and `<= 10` threshold present in Step 9E (grep check)
2. Did Step 9E fire on the next nightly after implementation? GH #399 comment added?
3. AUTOPILOT_GH_TOKEN rotated before 2026-09-20 (4 days from today, 12 days before expiry)?
4. Brain PAT rotation: GH issue filed?
5. SUPABASE_ACCESS_TOKEN: has human filled in rotation date?
6. Step 9G MCP fix (parking lot): verify `mcp__github__actions_run_trigger` available in nightly sessions + `kb-autopopulate.yml` has `workflow_dispatch`. If both confirmed → evaluate for run 122 implementation.
7. GH #875 (40 AI metering violations): has issue-to-pr-loop picked it up? If not (>24h since filing) → flag for human.

---

## Escalation Path

- Run 119 (2026-09-11): 1st appearance → RECOMMEND
- Run 120 (2026-09-11-pm): 1st carry-forward → RECOMMEND
- Run 121 (2026-09-16-pm, this run): 2nd carry-forward → RECOMMEND with escalation warning
- **Run 122: 3rd carry-forward → AUTONOMOUS-EXECUTABLE** (precedent: Steps 9F/9G/9I/9J/9K all auto-implemented on 3rd carry)
- Autonomous implementation requires: no human approval, direct SKILL.md edit + commit + push

**Critical path:** AUTOPILOT_GH_TOKEN expires 2026-10-02. Run 122 fires 2026-09-17. If Step 9E still unimplemented at run 122, autonomous implementation will fire with 15 days to expiry — adequate but tight.

---

## Why This Run Over Other Ideas

1. **Step 9G MCP fix** — Parking lot, not the winner. Fix would restore KB autopopulate triggering, but deeper blocker exists: GH #403 means the triggered workflow would fail anyway (missing ANTHROPIC_API_KEY). Fixing the trigger without fixing the underlying secret is a half-solution. Needs pre-verification before any recommendation.

2. **AI metering triage (GH #875)** — Already handled. Filed by nightly-2026-09-16, labeled `ai-ready`, issue-to-pr-loop should pick it up within 24h. Subconscious duplicating the signal adds noise, not value.

3. **os_tool_executions.py split** — Stability window broken (modified 2026-09-11, 5 days ago). No active bugs. Low urgency vs credential expiry.
