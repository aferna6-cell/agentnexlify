# Incident Response Playbook

_Last updated: 2026-04-20_

## Purpose
Use this playbook when a launch-readiness issue hits the repo, CI, or production.
It covers:

- failed PR validation with security findings
- leaked secrets or suspicious credential exposure
- broken deploys, degraded service, or data-risk incidents
- any issue that needs fast containment before root cause work

Related docs:

- `docs/ops/partner-runbook.md`
- `docs/ops/refund-runbook.md`
- `docs/ops/service-continuity-plan.md`

## Roles

- Incident lead: owns severity, decisions, and timeline
- Technical lead: isolates the failure and drives remediation
- Comms lead: posts updates to the team, stakeholders, or customers
- Scribe: records timestamps, actions, and outcomes

If only one person is available, they still assign these hats explicitly.

## Severity Guide

- P0: active security breach, data loss, or broad outage
- P1: customer-facing degradation or a high-confidence secret exposure
- P2: limited blast radius, workaround available, or CI/security failure blocking release
- P3: cosmetic or low-risk operational issue

When in doubt, start higher for security and data issues.

## First 15 Minutes

1. Confirm the signal is real.
2. Stop new exposure first: pause deploys, disable the suspect path, or block the affected integration.
3. Open a single incident thread and start the timeline.
4. Capture the blast radius: who is affected, what is broken, and whether data or credentials are involved.
5. Decide whether this is containment-only, rollback, secret rotation, or code fix.

## Containment Actions

- Roll back the last known bad deploy when the incident started after release.
- Revoke or rotate secrets immediately if they may be exposed.
- Disable the feature flag or route if the issue is isolated to one path.
- Remove public artifacts, logs, or screenshots that contain sensitive data.
- For CI security findings, do not bypass the gate; fix the source and re-run validation.

## Recovery

1. Apply the smallest change that stops the harm.
2. Re-run the failing check or reproduction.
3. Verify the fix with logs, metrics, or the exact CI job that failed.
4. Watch for recurrence long enough to trust the recovery.
5. Declare the incident resolved only after the signal stays clean.

## Communication Cadence

- P0/P1: update every 15 minutes until contained
- P2: update every 30 to 60 minutes
- P3: update when there is a meaningful change

Keep updates short:

- what happened
- what is affected
- what was done
- what happens next

## Security-Specific Rules

- Treat secret exposure as a live incident until proven otherwise.
- Assume leaked credentials are usable and act as if an attacker may already have them.
- Prefer revocation, rotation, and log review before deeper code hunting.
- Keep evidence intact for follow-up, but do not leave dangerous access in place.

## Aftercare

Within 48 hours:

1. Write a short post-incident summary.
2. Record the root cause and the decision that stopped the blast radius.
3. Add follow-up items with owners and due dates.
4. Update the playbook if the incident exposed a missing step.

## Minimal Post-Incident Template

```markdown
# Incident Summary

Date:
Severity:
Lead:
Status:

What happened:
Impact:
Containment:
Recovery:
Root cause:
Follow-up:
```
