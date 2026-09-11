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

## Proposal
**Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block:**

Add dedup-guarded auto-issue-filing when any credential is within 10 days of rotation threshold:

```
9E-escalation: For each credential in rotation-schedule:
  days_remaining = threshold - days_since_rotation
  If days_remaining <= 10:
    search_issues(query='ops(credentials): [CREDENTIAL_NAME] rotation due')
    If no open issue found:
      create_issue(
        title='ops(credentials): [CREDENTIAL_NAME] rotation due by [DATE] — human action required',
        body='Credential [NAME] last rotated [DATE]. Threshold [N] days. Due by [DEADLINE]. See ops/credential-rotation-schedule.md for rotation procedure.',
        labels=['human-action-required', 'ops'],
      )
      Log: 'Step 9E: filed rotation issue for [CREDENTIAL_NAME]'
    Else:
      Log: 'Step 9E: rotation issue already open for [CREDENTIAL_NAME], skipping'
```

## Expected Impact
- Zero-day outage prevention: AUTOPILOT_GH_TOKEN rotation becomes trackable in GH Issues
- Human gets a tangible action item (GH issue) vs a warning in a log they may not read
- Dedup guard prevents duplicate issues across nightly runs
- Applies to all credentials in rotation-schedule, not just AUTOPILOT_GH_TOKEN

## Autonomous-executable
YES — SKILL.md edit, proven channel, LOW risk. Only adds issue-filing; no code changed.
