# Winning Concept — Run 90 (2026-07-12)

**Date:** 2026-07-12
**Run:** 90
**Category:** operational
**Effort:** S
**Confidence:** HIGH
**Status:** AUTONOMOUS-EXECUTABLE (via mcp__github__push_files + mcp__github__create_pull_request)

---

## Recommendation

Create `.github/workflows/secrets-health-check.yml` — a zero-dependency GH Actions workflow that
validates ANTHROPIC_API_KEY and AUTOPILOT_GH_TOKEN are set and live on a weekly schedule, filing a
GH issue when either is missing or invalid.

---

## Why This, Why Now

The current 8-day pipeline stall (Day 8 as of this run) exposed a self-referential monitoring gap:
Step 9E in nightly-commit-review detects credential expiry, but Step 9E runs INSIDE the Claude
nightly workflow — which requires ANTHROPIC_API_KEY to execute. If that key goes missing in GH
Actions, Step 9E cannot fire to detect its own prerequisite failure. The result: silent multi-day
blackouts. This run's stall cost ~160h of blocked autonomous work (40 ai-ready issues × avg 4h
each) and extended KB degradation from 67 to 75+ days.

A GH Actions workflow using GITHUB_TOKEN (always present in GH Actions, no dependency on monitored
secrets) operates entirely outside the Claude stack. It pings Anthropic API and GitHub API directly
to confirm both keys are alive — not just non-empty. If either check fails, it creates a GH issue
with `human-action-required` label, the same P0 alerting path already familiar to the owner.

Steps 9B/9C/9D/9E all followed the same pattern: add a new monitoring layer → implemented within
1-2 cycles → prevented that failure class from going unnoticed. This is Step-9-pattern for the
credential monitoring's own blind spot.

---

## Implementation Sketch

**File:** `.github/workflows/secrets-health-check.yml`

**Exact file content to create:**

```yaml
name: Secrets Health Check

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday 9am UTC
  workflow_dispatch:       # Allow manual trigger

jobs:
  check-secrets:
    runs-on: ubuntu-latest
    steps:
      - name: Check ANTHROPIC_API_KEY present
        run: |
          if [ -z "${{ secrets.ANTHROPIC_API_KEY }}" ]; then
            echo "ANTHROPIC_API_KEY_MISSING=true" >> $GITHUB_ENV
          else
            echo "ANTHROPIC_API_KEY_MISSING=false" >> $GITHUB_ENV
          fi

      - name: Validate ANTHROPIC_API_KEY live
        if: env.ANTHROPIC_API_KEY_MISSING == 'false'
        run: |
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "x-api-key: ${{ secrets.ANTHROPIC_API_KEY }}" \
            -H "anthropic-version: 2023-06-01" \
            https://api.anthropic.com/v1/models)
          if [ "$STATUS" != "200" ]; then
            echo "ANTHROPIC_API_KEY_MISSING=true" >> $GITHUB_ENV
            echo "ANTHROPIC_API_KEY_FAIL_REASON=invalid_or_expired (HTTP $STATUS)" >> $GITHUB_ENV
          fi

      - name: Check AUTOPILOT_GH_TOKEN present
        run: |
          if [ -z "${{ secrets.AUTOPILOT_GH_TOKEN }}" ]; then
            echo "AUTOPILOT_GH_TOKEN_MISSING=true" >> $GITHUB_ENV
          else
            echo "AUTOPILOT_GH_TOKEN_MISSING=false" >> $GITHUB_ENV
          fi

      - name: Validate AUTOPILOT_GH_TOKEN live
        if: env.AUTOPILOT_GH_TOKEN_MISSING == 'false'
        run: |
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: token ${{ secrets.AUTOPILOT_GH_TOKEN }}" \
            https://api.github.com/user)
          if [ "$STATUS" != "200" ]; then
            echo "AUTOPILOT_GH_TOKEN_MISSING=true" >> $GITHUB_ENV
          fi

      - name: File alert issue if any secret is bad
        if: env.ANTHROPIC_API_KEY_MISSING == 'true' || env.AUTOPILOT_GH_TOKEN_MISSING == 'true'
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            const { data: issues } = await github.rest.issues.listForRepo({
              owner: context.repo.owner,
              repo: context.repo.repo,
              labels: 'secrets-health-check-alert',
              state: 'open',
              per_page: 1
            });
            if (issues.length > 0) {
              console.log('Alert issue already open — skipping creation');
              return;
            }
            const missing = [];
            if (process.env.ANTHROPIC_API_KEY_MISSING === 'true')
              missing.push('`ANTHROPIC_API_KEY` — blocks autopilot-issue-loop and kb-autopopulate');
            if (process.env.AUTOPILOT_GH_TOKEN_MISSING === 'true')
              missing.push('`AUTOPILOT_GH_TOKEN` — blocks autopilot-issue-loop');
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'ACTION REQUIRED: GH Actions secret missing or expired — autopilot pipeline blocked',
              labels: ['human-action-required', 'secrets-health-check-alert'],
              body: [
                '## Secrets Health Check Alert',
                '',
                'The weekly secrets health check found the following issues:',
                '',
                missing.map(m => `- ${m}`).join('\n'),
                '',
                '## Fix',
                '',
                '1. Go to **Settings → Secrets and variables → Actions** in this repo.',
                '2. Add or rotate the missing secret(s) listed above.',
                '3. For `ANTHROPIC_API_KEY`: generate at https://console.anthropic.com/settings/keys',
                '4. For `AUTOPILOT_GH_TOKEN`: generate at https://github.com/settings/tokens',
                '   - Required scopes: `repo`, `workflow`',
                '',
                '**Effort:** 2-5 minutes per secret.',
                '',
                '## Impact of not fixing',
                '',
                '- autopilot-issue-loop: all ai-ready issues stalled until fixed',
                '- kb-autopopulate: knowledge base stays stale',
                '- nightly-commit-review Steps 9D/9E: cannot run',
              ].join('\n')
            });
        env:
          ANTHROPIC_API_KEY_MISSING: ${{ env.ANTHROPIC_API_KEY_MISSING }}
          AUTOPILOT_GH_TOKEN_MISSING: ${{ env.AUTOPILOT_GH_TOKEN_MISSING }}
```

**Implementation steps:**
1. Create `.github/workflows/secrets-health-check.yml` with the content above via `mcp__github__push_files`
2. Commit message: `ops: add secrets health-check workflow — detect missing ANTHROPIC_API_KEY + AUTOPILOT_GH_TOKEN`
3. Open draft PR targeting `main`

**Verification:**
- After merging, navigate to Actions → Secrets Health Check → Run workflow (manual trigger)
- Confirm it detects the CURRENT missing ANTHROPIC_API_KEY (#403) on first run
- After owner sets #403 + #399, confirm workflow passes clean

---

## Bonus Action — Keys Koffee Business Hours GH Issue

File via GitHub MCP alongside this run's commit:

**Title:** `ACTION REQUIRED: Collect Keys Koffee business hours — 3rd tenant blocked on booking`

**Labels:** `human-action-required`, `revenue`

**Body:**
```markdown
## Status

MTOptions and 914 Exterior are now fully bookable (20 and 22 slots respectively, per PR #404).

Keys Koffee is the third paying tenant. It has NOT yet provided business hours, so zero booking
slots are available for their widget visitors.

## Action Required

Email Keys Koffee contact with their availability hours request.

**Template:**
> Hi [Keys Koffee contact],
>
> Your AI chat widget is live and capturing leads. We've now enabled online appointment booking
> for your account. To activate it, we need your business hours.
>
> Please reply with:
> - Days open (e.g., Mon-Fri, Sat)
> - Hours (e.g., 9am-5pm)
> - Any blackout days (holidays, etc.)
>
> Once we receive this, your customers will be able to book directly through the chat widget.

## Expected Outcome

- Keys Koffee becomes the 3rd fully bookable tenant
- Widget visitors can book appointments directly
- 3/3 paying tenants have the full booking feature activated

## Context

- PR #404 (2026-07-11): confirmed MTOptions and 914 Exterior bookable; Keys Koffee needs hours
- GH #412 (booking diagnostic SQL) will confirm Keys Koffee's booking_enabled status
- business hours are added via the dashboard → Business Settings → Availability
```

---

## What This Replaces

Previous active direction was referral reward activation (run 89 winner) — that direction is
unchanged and still pending (GH #413). This is a new operational direction addressing the root
cause of why the monitoring stack has a blind spot.

---

## Confidence

**HIGH** — Self-referential monitoring gap is structurally confirmed (Step 9E needs Claude API →
nightly needs ANTHROPIC_API_KEY → if that key expires, Step 9E never fires). GH Actions GITHUB_TOKEN
mechanism is a documented standard pattern. All 3 debate objections answered with evidence. File
content embedded for zero-ambiguity nightly execution.

---

## Run 91 Mandate

1. Verify `.github/workflows/secrets-health-check.yml` was created (check repo Actions tab).
2. Confirm first run result: did it detect the CURRENT missing ANTHROPIC_API_KEY (#403)?
3. Has owner set ANTHROPIC_API_KEY in GH Actions (#403)? Has AUTOPILOT_GH_TOKEN been rotated (#399)?
4. If pipeline restored: confirm issue-to-pr-loop picked up queued ai-ready issues. Lead Source
   Analytics GH #409 — draft PR opened?
5. Keys Koffee hours GH issue: was it filed? Any tenant response?
6. REFERRAL_REWARD_ENABLED=1 set in Railway? Any activity on GH #413?
7. Parking lot: Step 9F booking conversion tracker — file as run 91 winner if #403/#399 resolved.
