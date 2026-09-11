# Winning Concept — Run 2026-09-11-pm (Run 120)

**Winner:** Step 9E Credential Expiry Escalation — Earlier Warning + GH Issue Filing
**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH
**Carry-forward count:** 1 (1st carry-forward from run 119)
**Autonomous-executable threshold:** 3 consecutive carries → run 121 fires at run 122

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` tracks credential rotation age. Current logic:
- Fires when `days_since_rotation >= 76`
- Logs to nightly markdown file only
- Does NOT file a GH issue
- Does NOT comment on existing rotation tracking issue

Result: 3 consecutive nightlies logged "AUTOPILOT_GH_TOKEN approaching threshold" with zero human action. No GH issue = no email notification = no assignee = no audit trail.

AUTOPILOT_GH_TOKEN: 69d since rotation (threshold 76d, interval 90d). Expires 2026-10-02. If not rotated: autonomous loop dies.

Grep confirms Step 9E does NOT currently file GH issues:
- `grep 'add_issue_comment' SKILL.md` → 0 results in Step 9E block
- `grep 'days_remaining.*10\|<= 10' SKILL.md` → 0 results

---

## Implementation

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block.

**Change threshold logic:**
```
# Current (fires too late, no issue filed):
if days_since_rotation >= 76:
    log_warning("approaching threshold")

# New (fires earlier, files/comments on GH issue):
days_remaining = threshold_days - days_since_rotation  # threshold_days = 76
if days_remaining <= 10:  # fires at 66+ days since rotation
    # Dedup: search open issues by label "credential-rotation" + credential name
    # If existing open issue found: add comment with current days_remaining
    # If no open issue: create new issue with labels ["credential-rotation", "human-action-required", "ops"]
    mcp__github__search_issues(query=f"repo:aferna6-cell/agentnexlify is:open label:credential-rotation {credential_name}")
    if existing_issue:
        mcp__github__add_issue_comment(issue_number=existing_issue.number,
            body=f"Step 9E automated update: {credential_name} now at {days_since_rotation}d since rotation. {days_remaining}d remaining before {threshold_days}d threshold. Expires ~{expiry_date}. Action required: rotate in Railway → GitHub Secrets.")
    else:
        mcp__github__issue_write(title=f"Credential rotation required: {credential_name}",
            body=f"...", labels=["credential-rotation", "human-action-required", "ops"])
```

**Credentials to check:**
1. AUTOPILOT_GH_TOKEN — last_rotated: 2026-07-04, interval: 90d, threshold: 76d
2. Brain PAT — last_rotated: 2026-07-04, interval: 90d, threshold: 76d  
3. SUPABASE_ACCESS_TOKEN — last_rotated: unknown (human must fill in)

**Dedup guard (critical):** Search by label "credential-rotation" + credential name slug. GH #399 is the existing AUTOPILOT_GH_TOKEN rotation issue — comment on it rather than creating duplicate.

---

## Verification After Implementation

```bash
grep 'days_remaining' .claude/skills/nightly-commit-review/SKILL.md
grep '<= 10' .claude/skills/nightly-commit-review/SKILL.md
grep 'add_issue_comment' .claude/skills/nightly-commit-review/SKILL.md
```
All three must return results in Step 9E block.

Next nightly run: Step 9E should fire for AUTOPILOT_GH_TOKEN (69d > 66d threshold). GH #399 should receive a comment.

---

## Run 121 Mandate

1. Verify `days_remaining` and `<= 10` threshold present in Step 9E (grep check)
2. Did Step 9E fire on the next nightly after implementation? GH #399 comment added?
3. AUTOPILOT_GH_TOKEN rotated before 2026-09-18 (7 days from now)?
4. Brain PAT rotation: GH issue filed?
5. SUPABASE_ACCESS_TOKEN: has human filled in rotation date?
6. Step 9G MCP fix (Idea 2 from this run): evaluate for run 121 implementation
7. governance.json Step 9L stale flag: verify fixed (`implemented: true`, `verified_date` set)

---

## Escalation Path

- Run 120 (this run): 1st carry-forward → RECOMMEND
- Run 121: if not implemented → 2nd carry-forward → RECOMMEND with escalation flag
- Run 122: if not implemented → autonomous-executable (precedent: Steps 9F/9G/9I/9J/9K all auto-implemented on 3rd carry)
- Autonomous implementation requires: no human approval, direct SKILL.md edit + commit
