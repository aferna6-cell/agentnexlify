# Winning Concept — Run 119 (2026-09-11)

## Title
Step 9E credential expiry escalation: auto-file GH issue when token within 10 days of rotation threshold

## Category
workflow_efficiency / operational

## Evidence
- Nightly 2026-09-11 Step 9E: AUTOPILOT_GH_TOKEN at 69 days (threshold 76d, expires ~2026-09-18 — 7 days)
- Brain connector GitHub PAT: same age, same deadline
- Step 9E current behavior: logs warning only. No GH issue filed. No human-action escalation.
- 3 consecutive nightlies (Sep 9-11) flagged the warning; zero human action observed
- AUTOPILOT_GH_TOKEN powers the autonomous engineering loop (nightly-commit-review, issue-to-pr-loop)
- If it expires: all autonomous review, fix, and escalation stops. CVE window stays open. Stale issues accumulate.
- ops/credential-rotation-schedule.md exists but has no automated escalation trigger

## Autonomous-executable
YES — SKILL.md edit, proven channel. Same pattern as Steps 9F/9G/9I/9J/9K implementations.

## Action

**Edit `.claude/skills/nightly-commit-review/SKILL.md` — Step 9E block.**

Find the Step 9E section (credential rotation status check). After the existing status-logging logic, add a conditional GH issue escalation block:

### Step 9E escalation block (add after existing credential age check):

NOTE on dedup: search must use credential identity (token name), NOT an exact
proposed title. This prevents duplicates even when existing issues use a
different title format (e.g. GH #399 already tracks AUTOPILOT_GH_TOKEN rotation
under a different title). When an existing issue is found, add a comment with
the updated deadline — do not create a duplicate.

```
9E-escalation: Credential rotation auto-escalation.
    For each credential in ops/credential-rotation-schedule.md:
      days_since_rotation = (today - last_rotated_date).days
      days_remaining = threshold_days - days_since_rotation
      If days_remaining <= 10:
        # Search by credential name across open human-action/ops issues,
        # NOT by exact proposed title — avoids duplicating existing trackers
        # (e.g. GH #399 already tracks AUTOPILOT_GH_TOKEN with a different title).
        existing = search_issues(
          query='{CREDENTIAL_NAME} is:open label:human-action-required repo:aferna6-cell/agentnexlify'
        )
        If no open issue found:
          # Also try label:ops in case labeled differently
          existing = search_issues(
            query='{CREDENTIAL_NAME} is:open label:ops repo:aferna6-cell/agentnexlify'
          )
        If no open issue found after both searches:
          create_issue(
            owner='aferna6-cell',
            repo='agentnexlify',
            title='ops(credentials): {CREDENTIAL_NAME} rotation due by {DEADLINE_DATE} — human action required',
            body=(
              'Automated credential rotation alert.\n\n'
              '**Credential**: {CREDENTIAL_NAME}\n'
              '**Last rotated**: {LAST_ROTATED}\n'
              '**Rotation threshold**: {THRESHOLD} days\n'
              '**Days since rotation**: {DAYS_SINCE}\n'
              '**Rotation deadline**: {DEADLINE_DATE}\n\n'
              'See `ops/credential-rotation-schedule.md` for rotation procedure.\n\n'
              'Close this issue once rotation is complete.'
            ),
            labels=['human-action-required', 'ops', 'P0']
          )
          Log: 'Step 9E: filed rotation issue for {CREDENTIAL_NAME} (due {DEADLINE_DATE})'
        Else:
          # Update existing issue with current deadline — do NOT create duplicate
          add_issue_comment(
            owner='aferna6-cell',
            repo='agentnexlify',
            issue_number=existing[0].number,
            body=(
              'Automated credential rotation update (Step 9E nightly check).\n\n'
              '**Credential**: {CREDENTIAL_NAME}\n'
              '**Days since rotation**: {DAYS_SINCE}d\n'
              '**Rotation deadline**: {DEADLINE_DATE} ({DAYS_REMAINING}d remaining)\n\n'
              'Action required: rotate before deadline to avoid autonomous loop failure.'
            )
          )
          Log: 'Step 9E: commented on existing issue #{existing[0].number} for {CREDENTIAL_NAME} (due {DEADLINE_DATE})'
      Else:
        Log: 'Step 9E: {CREDENTIAL_NAME} at {DAYS_SINCE}d — {DAYS_REMAINING}d to threshold. PASS.'
```

### Credentials to include
From `ops/credential-rotation-schedule.md`:
- AUTOPILOT_GH_TOKEN (last rotated: 2026-07-04, threshold: 76d)
- Brain connector GitHub PAT (last rotated: 2026-07-04, threshold: 76d)
- SUPABASE_ACCESS_TOKEN (unknown — treat as requires-verification)

### Impact
- Immediate: AUTOPILOT_GH_TOKEN already tracked by GH #399 — Step 9E will add a comment there with updated deadline. Brain PAT: Step 9E searches and either comments on existing issue or files new one.
- Permanent: all future credentials auto-escalate before expiry
- Dedup guard (credential-name search, not exact-title match) prevents duplicate issues even when existing tracker uses a different title format
- Loop death from credential expiry becomes impossible to miss (P0 label, GH notification, nightly comment updates)

## Bonus Actions (bundle in same commit)

### Bonus A: Fix governance.json Step 9L stale flag
Change `active_directions.step_9l_ai_metering.implemented` from `false` to `true` and status from `pending_approval` to `verified_implemented`. Add `verified_date: "2026-09-10-pm"`.

### Bonus B: Create initial step9j-cursor.json
Run 118 winning concept was never implemented (cursor file missing). With 0 Dependabot PRs currently, Step 9J cursor approach is moot. Skip implementation; note in governance.json.

## Verification
After SKILL.md edit:
- grep 'days_remaining.*10' .claude/skills/nightly-commit-review/SKILL.md → must return the escalation condition line
- grep 'human-action-required.*ops' .claude/skills/nightly-commit-review/SKILL.md → must return the label line
- grep 'add_issue_comment' .claude/skills/nightly-commit-review/SKILL.md → must return the update-existing-issue branch
- Next nightly: check GH #399 for a new Step 9E comment with updated deadline (not a new issue)

## Risk
Near-zero. Additive only — existing Step 9E credential-detection logic unchanged. GH issue filing uses mcp__github__create_issue (same as Step 9D/9I/9L). Dedup guard prevents duplicates. The only new behavior is issue creation on credential-near-expiry.

## Mandate for Run 120
1. Check GH #399 — is AUTOPILOT_GH_TOKEN rotation resolved? (look for close or rotation confirmation comment)
2. Verify Step 9E implementation was approved and added to SKILL.md — check for 'add_issue_comment' in nightly-commit-review SKILL.md
3. Verify Brain PAT rotation GH issue status — search open issues for 'Brain connector GitHub PAT'
4. Report SUPABASE_ACCESS_TOKEN status (unknown — ops/credential-rotation-schedule.md shows 'unknown state')
5. Secondary: verify Step 9G mcp fix is viable (check kb-autopopulate.yml has workflow_dispatch trigger)
