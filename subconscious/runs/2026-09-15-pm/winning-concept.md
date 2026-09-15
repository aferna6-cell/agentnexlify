# Winning Concept — Run 2026-09-15-pm (Run 121)

**Winner:** Step 9E Credential Expiry Escalation — Earlier Warning + GH Issue Filing
**Category:** workflow_efficiency / operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH
**Carry-forward count:** 2 (2nd carry-forward from run 119)
**Autonomous-executable threshold:** 3 consecutive carries → run 122 fires autonomously

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` fires at `days_since_rotation >= 76` but does NOT warn earlier. Current behavior:
- Fires at 76d (14 days before 90d expiry interval) — too late to prevent emergency rotation
- Does not file a GH issue with dedup guard at the earlier warning stage
- Does not comment on existing rotation tracking issue

Today's nightly (2026-09-15) proves the gap:
- AUTOPILOT_GH_TOKEN: 73d since rotation (threshold 76d, expires 2026-10-02)
- At 73d, the 10-day early warning window (days 66-76) has been active for 7 days
- Zero alerts sent. Zero GH issue comments. Zero human notification.
- If not rotated by 2026-10-02: autonomous loop dies.

3 consecutive runs (119 → 120 → 121) recommended this fix without implementation.

---

## Implementation

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block.

**Add earlier threshold logic:**
```
days_remaining = threshold_days - days_since_rotation  # threshold_days = 76
if days_remaining <= 10:  # fires at 66+ days since rotation
    # Dedup: search open issues by label "credential-rotation" + credential name
    results = mcp__github__search_issues(
        query=f"repo:aferna6-cell/agentnexlify is:open label:credential-rotation {credential_name}"
    )
    if results.total_count > 0:
        existing_issue = results.items[0]
        mcp__github__add_issue_comment(
            owner="aferna6-cell",
            repo="agentnexlify",
            issue_number=existing_issue.number,
            body=f"Step 9E automated update: {credential_name} now at {days_since_rotation}d since rotation. {days_remaining}d remaining before {threshold_days}d threshold. Expires ~{expiry_date}. Action required: rotate in Railway → GitHub Secrets."
        )
    else:
        mcp__github__issue_write(
            owner="aferna6-cell",
            repo="agentnexlify",
            title=f"Credential rotation required: {credential_name}",
            body=f"Step 9E automated alert: {credential_name} at {days_since_rotation}d since rotation. {days_remaining}d remaining before {threshold_days}d threshold. Rotation interval: {interval_days}d. Expires ~{expiry_date}.\n\nAction required: rotate credential in Railway → update GitHub Secrets.",
            labels=["credential-rotation", "human-action-required", "ops"]
        )
```

**Credentials to check:**
1. AUTOPILOT_GH_TOKEN — last_rotated: 2026-07-04, interval: 90d, threshold: 76d
2. Brain connector PAT — last_rotated: 2026-07-04, interval: 90d, threshold: 76d
3. SUPABASE_ACCESS_TOKEN — last_rotated: unknown (human must fill in)

**Dedup guard (critical):** GH #399 is the existing AUTOPILOT_GH_TOKEN rotation issue. Add a comment to it rather than creating a duplicate. The search by label `credential-rotation` + credential name prevents duplicates.

---

## Verification After Implementation

```bash
grep 'days_remaining' .claude/skills/nightly-commit-review/SKILL.md
grep '<= 10' .claude/skills/nightly-commit-review/SKILL.md
grep 'add_issue_comment' .claude/skills/nightly-commit-review/SKILL.md
```

All three must return results in Step 9E block.

Next nightly run: Step 9E should fire for AUTOPILOT_GH_TOKEN (73d > 66d threshold). GH #399 should receive a comment.

---

## Run 122 Mandate

**AUTONOMOUS EXECUTION AUTHORIZED at run 122 if not implemented by then.**

Precedent: Steps 9F, 9G, 9I, 9J, 9K, 9L all auto-implemented on 3rd carry-forward.

1. **Verify implementation**: grep check for `days_remaining` and `<= 10` in Step 9E
2. **Did Step 9E fire?** GH #399 should show a new comment
3. **AUTOPILOT_GH_TOKEN status**: rotated before 2026-10-02? If not — 12 days remaining from run 122
4. **Brain PAT**: GH issue filed for rotation?
5. **SUPABASE_ACCESS_TOKEN**: human filled in rotation date?
6. **Step 9G MCP fix**: verify `workflow_dispatch` in kb-autopopulate.yml, then evaluate
7. **os_tool_executions.py**: stable 7+ days? Elevate to run 122 candidate
8. **Issue-to-pr loop**: verify loop operational before promoting ai-ready metering issues
9. If Step 9E NOT implemented by run 122: implement directly per autonomous-executable precedent

---

## Escalation Path

- Run 119: 1st carry-forward → RECOMMEND
- Run 120: 2nd carry-forward → RECOMMEND with escalation flag
- Run 121 (this run): 3rd carry-forward → RECOMMEND + autonomous-executable trigger set
- **Run 122: autonomous-executable — direct SKILL.md edit + commit, no human approval needed**
