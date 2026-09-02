# Branch protection blocker — 2026-09-02

## Desired state

Require PR Validation on `main` (see `planning/milestone-9-persistent-planner-kickoff.md`).

## Observed

```text
GET /repos/aferna6-cell/agentnexlify/branches/main/protection
→ 403 Resource not accessible by integration

GET /repos/aferna6-cell/agentnexlify/rulesets
→ 403 Upgrade to GitHub Pro or make this repository public
```

Repository is **private**. Making it public solely for rulesets is rejected.

## Resolution path

1. Upgrade the owning account/org to **GitHub Pro** (or equivalent that unlocks private-repo branch protection / rulesets).
2. Apply the desired `main` rule: PR required, `PR Validation` required, up-to-date branch, no direct/force pushes, no deletion, narrow owner break-glass.
3. Keep the Auto Log Bug Fix workflow on **PR-based writes** (companion change) so docs bots never bypass protection once enabled.

Until then, treat unprotected `main` as an accepted temporary governance debt — do not weaken CI or reopen direct bot pushes.
