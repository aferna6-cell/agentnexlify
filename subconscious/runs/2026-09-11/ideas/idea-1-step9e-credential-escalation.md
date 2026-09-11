# Idea 1 — Step 9E Credential Escalation: Auto-file GH Issue When Token Within 10 Days

## Category
workflow_efficiency / operational

## Evidence
- Nightly 2026-09-11: Step 9E found AUTOPILOT_GH_TOKEN at 69 days (threshold 76d) — expires ~2026-09-18 (~7 days)
- Brain connector GitHub PAT: same age, same deadline
- Step 9E current behavior: logs warning + comments on GH #800 (brain connector staleness) — NO dedicated rotation GH issue filed
- ops/credential-rotation-schedule.md exists with rotation dates, but no automated escalation mechanism
- AUTOPILOT_GH_TOKEN powers the entire autonomous engineering loop — if it expires, all nightly reviews and issue-to-PR automation dies silently
- 3 consecutive nightlies (Sep 9-11) have flagged this without human action
- Existing open GH #399 already tracks AUTOPILOT_GH_TOKEN under a different title, and GH #394 already tracks the Brain GitHub credential problem

## Proposal
**Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block:**

Add dedup-guarded auto-issue-filing when any credential is within 10 days of rotation threshold. Dedup MUST search by credential identity across existing open human-action/operational issues, not by an exact proposed title. Reuse/update an existing tracker when found.

```
9E-escalation: For each credential in rotation-schedule:
  days_remaining = threshold - days_since_rotation
  If days_remaining <= 10:
    existing = search_issues(query='[CREDENTIAL_NAME] is:open label:human-action-required repo:aferna6-cell/agentnexlify')
    If no open issue found:
      existing = search_issues(query='[CREDENTIAL_NAME] is:open label:operational repo:aferna6-cell/agentnexlify')
    If no open issue found after both searches:
      create_issue(
        title='ops(credentials): [CREDENTIAL_NAME] rotation due by [DATE] — human action required',
        body='Credential [NAME] last rotated [DATE]. Threshold [N] days. Due by [DEADLINE]. See ops/credential-rotation-schedule.md for rotation procedure.',
        labels=['human-action-required', 'ops', 'P0'],
      )
      Log: 'Step 9E: filed rotation issue for [CREDENTIAL_NAME]'
    Else:
      add_issue_comment(
        issue_number=existing[0].number,
        body='Automated credential rotation update: [CREDENTIAL_NAME] due by [DEADLINE] ([DAYS_REMAINING] days remaining).'
      )
      Log: 'Step 9E: updated existing credential issue for [CREDENTIAL_NAME], no duplicate filed'
```

## Expected Impact
- Zero-day outage prevention: AUTOPILOT_GH_TOKEN rotation remains trackable via existing GH #399 rather than creating a duplicate
- Brain credential escalation can reuse GH #394 when it matches the credential identity
- Human gets a tangible action item or refreshed existing tracker instead of a warning in a log they may not read
- Credential-name dedup prevents duplicate issues even when existing titles differ from the proposed title format
- Applies to all credentials in rotation-schedule, not just AUTOPILOT_GH_TOKEN

## Autonomous-executable
YES — SKILL.md edit, proven channel, LOW risk. Only adds issue-filing/commenting; no runtime product code changed.
